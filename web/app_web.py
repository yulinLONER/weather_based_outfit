import os
import sys
import json
import base64
import uuid
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect
from PIL import Image
from typing import Any, Dict, Optional, Tuple

# 将项目根目录添加到 python 路径，确保可以导入 api 和 core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.weather_service import WeatherService
from api.ai_tools import AISettingsStore, ai_recommend, generate_ai_tags
from core.ai_client import AIClientError, chat_json, is_ai_enabled
from core.recommender import OutfitRecommender
from db.manager import WardrobeDatabase

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 生产环境下必须设置 FLASK_SECRET_KEY
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "ERROR: FLASK_SECRET_KEY environment variable must be set in production. "
            "Please set it in your .env file or environment."
        )
    # 开发环境下使用临时密钥（仅用于测试）
    app.secret_key = "dev-secret-key-change-in-production"
    app.logger.warning("⚠️  Using dev secret key - DO NOT USE IN PRODUCTION")

# 强制禁用 Jinja2 模板缓存，确保每次都能读取最新的 index.html
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 初始化后端服务
weather_svc = WeatherService()
recommender = OutfitRecommender()
db_manager = WardrobeDatabase()
ai_settings = AISettingsStore(db_manager)


def _is_admin_authed() -> bool:
    return bool(session.get("is_admin"))


def _require_admin():
    if not _is_admin_authed():
        return redirect("/admin/login")
    return None


def _coerce_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _get_functional_tags(cursor):
    cursor.execute("SELECT id, name FROM functional_tags ORDER BY name")
    return [dict(row) for row in cursor.fetchall()]


def _get_tag_name_to_id(cursor):
    cursor.execute("SELECT id, name FROM functional_tags")
    return {row["name"]: int(row["id"]) for row in cursor.fetchall()}


def _get_tag_id_to_name(cursor):
    cursor.execute("SELECT id, name FROM functional_tags")
    return {int(row["id"]): row["name"] for row in cursor.fetchall()}


def _parse_tag_ids(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    ids = []
    for v in _coerce_list(raw):
        try:
            ids.append(int(v))
        except Exception:
            continue
    return ids


def _parse_seasons(raw):
    allowed = {"春", "夏", "秋", "冬"}
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    seasons = []
    for v in _coerce_list(raw):
        if isinstance(v, str) and v in allowed:
            seasons.append(v)
    return seasons


def _uploads_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "uploads_tmp")
    os.makedirs(path, exist_ok=True)
    return path


def _validate_image_bytes(raw: bytes) -> Tuple[str, Image.Image]:
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("图片超过 5MB 限制")
    try:
        im = Image.open(BytesIO(raw))
        im.load()
    except Exception:
        raise ValueError("无法解析图片")
    fmt = (im.format or "").upper()
    allowed = {"JPEG", "JPG", "PNG", "WEBP"}
    if fmt not in allowed:
        raise ValueError("不支持的图片格式（仅 JPG/PNG/WEBP）")
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    mime = "image/jpeg" if fmt in {"JPEG", "JPG"} else ("image/png" if fmt == "PNG" else "image/webp")
    return mime, im


def _process_image(im: Image.Image, crop: Optional[Dict[str, Any]] = None) -> Tuple[bytes, str, int, int]:
    if crop:
        try:
            x = float(crop.get("x", 0))
            y = float(crop.get("y", 0))
            w = float(crop.get("w", 0))
            h = float(crop.get("h", 0))
            if w > 0 and h > 0:
                x0 = max(0, int(round(x)))
                y0 = max(0, int(round(y)))
                x1 = min(im.width, int(round(x + w)))
                y1 = min(im.height, int(round(y + h)))
                if x1 > x0 and y1 > y0:
                    im = im.crop((x0, y0, x1, y1))
        except Exception:
            pass

    max_side = 1024
    if max(im.width, im.height) > max_side:
        im.thumbnail((max_side, max_side))

    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")

    out = BytesIO()
    im.save(out, format="WEBP", quality=82, method=6)
    data = out.getvalue()
    return data, "image/webp", im.width, im.height


def _store_image(product_id: int, raw: bytes, crop: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _, im = _validate_image_bytes(raw)
    data, mime, w, h = _process_image(im, crop=crop)
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO wardrobe_images (product_id, image_blob, mime_type, width, height, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(product_id) DO UPDATE SET
            image_blob=excluded.image_blob,
            mime_type=excluded.mime_type,
            width=excluded.width,
            height=excluded.height,
            updated_at=CURRENT_TIMESTAMP
        """,
        (product_id, data, mime, w, h),
    )
    conn.commit()
    conn.close()
    return {"mime": mime, "width": w, "height": h, "bytes": len(data)}

@app.after_request
def add_header(response):
    """强制浏览器不缓存，避免前端代码更新后用户仍在使用旧版缓存"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.before_request
def ensure_user_id():
    if not session.get("uid"):
        session["uid"] = uuid.uuid4().hex

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = (request.form.get("password") or "").strip()
        admin_pw = os.environ.get("ADMIN_PASSWORD", "")
        if admin_pw and password == admin_pw:
            session["is_admin"] = True
            return redirect("/admin")
        error = "密码错误或未设置 ADMIN_PASSWORD"
    return render_template("admin_login.html", error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect("/")


@app.route('/admin')
def admin_index():
    r = _require_admin()
    if r:
        return r
    return render_template("admin.html")


@app.route('/admin/api/settings', methods=['GET'])
def admin_get_settings():
    r = _require_admin()
    if r:
        return r

    def _get(k, default=None):
        return ai_settings.get(k, default)

    return jsonify(
        {
            "ai_enabled": is_ai_enabled(),
            "api_base_url": _get("api_base_url", ""),
            "model": _get("model", ""),
            "timeout_seconds": int(_get("timeout_seconds", "30") or 30),
            "tag_min_confidence": float(_get("tag_min_confidence", "0.65") or 0.65),
            "tag_max_tags": int(_get("tag_max_tags", "6") or 6),
            "recommend_cache_ttl_seconds": int(_get("recommend_cache_ttl_seconds", "600") or 600),
            "recommend_max_candidates": int(_get("recommend_max_candidates", "80") or 80),
            "recommend_strategy": _get("recommend_strategy", "balanced"),
            "weight_style": float(_get("weight_style", "1.0") or 1.0),
            "weight_season": float(_get("weight_season", "1.0") or 1.0),
            "weight_tags": float(_get("weight_tags", "0.7") or 0.7),
        }
    )


@app.route('/admin/api/settings/ai', methods=['POST'])
def admin_set_ai_settings():
    r = _require_admin()
    if r:
        return r
    data = request.json or {}
    api_base_url = (data.get("api_base_url") or "").strip()
    model = (data.get("model") or "").strip()
    timeout_seconds = str(data.get("timeout_seconds") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    if api_base_url:
        ai_settings.set("api_base_url", api_base_url)
    if model:
        ai_settings.set("model", model)
    if timeout_seconds:
        ai_settings.set("timeout_seconds", timeout_seconds)
    if api_key:
        ai_settings.set("api_key", api_key)

    return jsonify({"success": True})


@app.route('/admin/api/settings/tags', methods=['POST'])
def admin_set_tag_settings():
    r = _require_admin()
    if r:
        return r
    data = request.json or {}
    ai_settings.set("tag_min_confidence", str(data.get("tag_min_confidence") or "0.65"))
    ai_settings.set("tag_max_tags", str(data.get("tag_max_tags") or "6"))
    return jsonify({"success": True})


@app.route('/admin/api/settings/recommend', methods=['POST'])
def admin_set_recommend_settings():
    r = _require_admin()
    if r:
        return r
    data = request.json or {}
    ai_settings.set("recommend_cache_ttl_seconds", str(data.get("recommend_cache_ttl_seconds") or "600"))
    ai_settings.set("recommend_max_candidates", str(data.get("recommend_max_candidates") or "80"))
    ai_settings.set("recommend_strategy", str(data.get("recommend_strategy") or "balanced"))
    ai_settings.set("weight_style", str(data.get("weight_style") or "1.0"))
    ai_settings.set("weight_season", str(data.get("weight_season") or "1.0"))
    ai_settings.set("weight_tags", str(data.get("weight_tags") or "0.7"))
    return jsonify({"success": True})

@app.route('/api/weather', methods=['POST'])
def get_weather():
    """获取天气信息的 API"""
    data = request.json
    province = data.get('province', '北京')
    city = data.get('city', '北京')
    
    weather_data = weather_svc.get_weather(province, city)
    return jsonify(weather_data)


@app.route('/api/events', methods=['POST'])
def track_event():
    data = request.json or {}
    event_type = (data.get("event_type") or "").strip()
    item_id = data.get("item_id")
    meta = data.get("meta") or {}
    if not event_type:
        return jsonify({"success": False, "error": "缺少 event_type"}), 400
    try:
        item_id_int = int(item_id) if item_id is not None else None
    except Exception:
        item_id_int = None
    try:
        meta_json = json.dumps(meta, ensure_ascii=False)
    except Exception:
        meta_json = "{}"

    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_events (user_id, event_type, item_id, meta_json) VALUES (?, ?, ?, ?)",
        (session.get("uid"), event_type, item_id_int, meta_json),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/recommend', methods=['POST'])
def get_recommendation():
    """获取穿搭推荐的 API"""
    data = request.json
    temp = data.get('temperature')
    weather = data.get('weather')
    style = data.get('style')
    use_ai = bool(data.get("use_ai"))
    
    if style == "全部" or not style:
        style = None

    recommendations, info = recommender.get_recommendations(temp, weather, style)

    if use_ai:
        try:
            user_id = session.get("uid")
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            season = info.get("season", "春")
            params = [f"%{season}%"]
            query = """
                SELECT DISTINCT
                    p.id,
                    p.title,
                    p.style,
                    c.name as category,
                    pc.name as parent_category,
                    s.color_name,
                    s.size_name,
                    s.tag_ids,
                    s.price
                FROM products p
                JOIN product_skus s ON p.id = s.product_id
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN categories pc ON c.parent_id = pc.id
                WHERE s.seasons LIKE ? AND s.is_active = 1
            """
            if style:
                query += " AND p.style = ?"
                params.append(style)
            query += " ORDER BY c.name, p.created_at DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            tag_id_to_name = _get_tag_id_to_name(cursor)
            candidates = []
            for r in rows:
                tag_ids = _parse_tag_ids(r["tag_ids"])
                tag_names = [tag_id_to_name.get(tid) for tid in tag_ids]
                tag_names = [t for t in tag_names if t]
                candidates.append(
                    {
                        "id": int(r["id"]),
                        "title": r["title"],
                        "category": r["category"],
                        "parent_category": r["parent_category"],
                        "style": r["style"] or "休闲",
                        "color": r["color_name"] or "",
                        "size": r["size_name"] or "",
                        "price": float(r["price"] or 0),
                        "tags": tag_names,
                    }
                )
            conn.close()

            recent_prefs = {}
            try:
                conn2 = db_manager.get_connection()
                cur2 = conn2.cursor()
                cur2.execute(
                    """
                    SELECT event_type, meta_json
                    FROM user_events
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 30
                    """,
                    (user_id,),
                )
                evs = [dict(r) for r in cur2.fetchall()]
                conn2.close()
                styles = []
                for e in evs:
                    if e.get("event_type") != "recommend_request":
                        continue
                    try:
                        meta = json.loads(e.get("meta_json") or "{}")
                    except Exception:
                        meta = {}
                    s = meta.get("style")
                    if isinstance(s, str) and s:
                        styles.append(s)
                recent_prefs = {"recent_styles": styles[:10]}
            except Exception:
                recent_prefs = {}

            weather_info = {
                "temperature": info.get("temperature"),
                "weather": info.get("weather"),
                "season": info.get("season"),
                "style_preference": info.get("style_preference"),
                "recent_preferences": recent_prefs,
                "strategy": ai_settings.get("recommend_strategy", "balanced"),
                "weights": {
                    "style": float(ai_settings.get("weight_style", "1.0") or 1.0),
                    "season": float(ai_settings.get("weight_season", "1.0") or 1.0),
                    "tags": float(ai_settings.get("weight_tags", "0.7") or 0.7),
                },
            }

            cfg = ai_settings.as_recommend_config()
            ai_obj = ai_recommend(weather_info=weather_info, candidates=candidates, config=cfg, db=db_manager)
            if isinstance(ai_obj, dict) and isinstance(ai_obj.get("recommendations"), dict):
                recommendations = ai_obj["recommendations"]
                info["ai_tip"] = ai_obj.get("ai_tip")
        except AIClientError as e:
            info["ai_error"] = str(e)
        except Exception as e:
            info["ai_error"] = str(e)
    
    return jsonify({
        'recommendations': recommendations,
        'info': info
    })

@app.route('/api/wardrobe', methods=['GET'])
def get_wardrobe():
    """获取衣橱列表"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.title, p.category_id, c.name as category, b.name as brand, 
               p.main_image, p.base_price, p.style,
               MAX(s.color_name) as color,
               MAX(s.size_name) as size,
               MAX(s.seasons) as seasons,
               MAX(s.tag_ids) as tag_ids,
               CASE WHEN wi.product_id IS NULL THEN 0 ELSE 1 END as has_image
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN product_skus s ON p.id = s.product_id
        LEFT JOIN wardrobe_images wi ON p.id = wi.product_id
        GROUP BY p.id
        ORDER BY p.created_at DESC
    ''')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/wardrobe', methods=['POST'])
def add_wardrobe_item():
    """添加衣橱商品"""
    data = request.json
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        # 1. 处理品牌
        brand_name = data.get('brand', '未知品牌')
        cursor.execute("SELECT id FROM brands WHERE name = ?", (brand_name,))
        brand_row = cursor.fetchone()
        brand_id = brand_row['id'] if brand_row else None
        if not brand_id:
            cursor.execute("INSERT INTO brands (name) VALUES (?)", (brand_name,))
            brand_id = cursor.lastrowid
            
        # 2. 插入商品
        cursor.execute('''
            INSERT INTO products (platform, platform_id, brand_id, category_id, title, base_price, style)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Manual', str(int(datetime.now().timestamp())), brand_id, 
            data.get('category_id', 1), data.get('title'), data.get('price', 0), data.get('style', '休闲')
        ))
        product_id = cursor.lastrowid
        
        # 3. 插入默认 SKU
        seasons = data.get("seasons", ['春', '夏', '秋', '冬'])
        seasons = _parse_seasons(seasons) or ['春', '夏', '秋', '冬']
        tag_ids = _parse_tag_ids(data.get("tag_ids"))
        cursor.execute('''
            INSERT INTO product_skus (product_id, color_name, size_name, seasons, tag_ids, price, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id, data.get('color', '默认'), data.get('size', 'M'),
            json.dumps(seasons, ensure_ascii=False),
            json.dumps(tag_ids, ensure_ascii=False),
            data.get('price', 0), 10
        ))
        
        conn.commit()
        return jsonify({'success': True, 'id': product_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/api/wardrobe/<int:item_id>', methods=['PUT'])
def edit_wardrobe_item(item_id):
    """编辑衣橱商品"""
    data = request.json
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        # 1. 处理品牌
        brand_name = data.get('brand', '未知品牌')
        cursor.execute("SELECT id FROM brands WHERE name = ?", (brand_name,))
        brand_row = cursor.fetchone()
        brand_id = brand_row['id'] if brand_row else None
        if not brand_id:
            cursor.execute("INSERT INTO brands (name) VALUES (?)", (brand_name,))
            brand_id = cursor.lastrowid
            
        # 2. 更新主商品表
        cursor.execute('''
            UPDATE products 
            SET title = ?, category_id = ?, brand_id = ?, base_price = ?, style = ?
            WHERE id = ?
        ''', (
            data.get('title'), data.get('category_id'), brand_id, 
            data.get('price', 0), data.get('style', '休闲'), item_id
        ))
        
        # 3. 更新对应的 SKU（简化为更新该商品下所有 SKU 的关键字段）
        seasons = data.get("seasons")
        seasons = _parse_seasons(seasons) if seasons is not None else None
        tag_ids = data.get("tag_ids")
        tag_ids = _parse_tag_ids(tag_ids) if tag_ids is not None else None
        seasons_json = json.dumps(seasons, ensure_ascii=False) if seasons is not None else None
        tag_ids_json = json.dumps(tag_ids, ensure_ascii=False) if tag_ids is not None else None

        cursor.execute('''
            UPDATE product_skus
            SET color_name = ?, size_name = ?, price = ?,
                seasons = COALESCE(?, seasons),
                tag_ids = COALESCE(?, tag_ids)
            WHERE product_id = ?
        ''', (
            data.get('color', '默认'), data.get('size', 'M'), data.get('price', 0),
            seasons_json, tag_ids_json,
            item_id
        ))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/api/wardrobe/<int:item_id>', methods=['DELETE'])
def delete_wardrobe_item(item_id):
    """删除衣橱商品"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM product_skus WHERE product_id = ?", (item_id,))
        cursor.execute("DELETE FROM products WHERE id = ?", (item_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@app.route('/api/wardrobe/<int:item_id>/image', methods=['GET'])
def get_wardrobe_image(item_id):
    size = (request.args.get("size") or "small").strip().lower()
    max_side = 320 if size == "small" else (768 if size == "medium" else 1400)
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT image_blob, mime_type FROM wardrobe_images WHERE product_id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return ("", 404)
    raw = row["image_blob"]
    mime = row["mime_type"]

    try:
        im = Image.open(BytesIO(raw))
        im.load()
        if max(im.width, im.height) > max_side:
            im.thumbnail((max_side, max_side))
        out = BytesIO()
        im.save(out, format="WEBP", quality=80, method=6)
        raw = out.getvalue()
        mime = "image/webp"
    except Exception:
        pass

    return raw, 200, {"Content-Type": mime, "Cache-Control": "public, max-age=300"}


@app.route('/api/uploads/init', methods=['POST'])
def init_upload():
    data = request.json or {}
    filename = (data.get("filename") or "upload").strip()
    mime = (data.get("mime") or "").strip().lower()
    size = int(data.get("size") or 0)
    if size <= 0:
        return jsonify({"success": False, "error": "无效文件大小"}), 400
    if size > 5 * 1024 * 1024:
        return jsonify({"success": False, "error": "图片超过 5MB 限制"}), 400
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        return jsonify({"success": False, "error": "不支持的图片格式（仅 JPG/PNG/WEBP）"}), 400

    upload_id = uuid.uuid4().hex
    path = os.path.join(_uploads_dir(), f"{upload_id}.part")
    meta_path = os.path.join(_uploads_dir(), f"{upload_id}.json")
    with open(path, "wb") as f:
        f.truncate(0)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"filename": filename, "mime": mime, "size": size, "created_at": datetime.utcnow().isoformat()}, f, ensure_ascii=False)
    return jsonify({"success": True, "upload_id": upload_id})


@app.route('/api/uploads/<upload_id>/status', methods=['GET'])
def upload_status(upload_id):
    path = os.path.join(_uploads_dir(), f"{upload_id}.part")
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "上传不存在"}), 404
    received = os.path.getsize(path)
    return jsonify({"success": True, "received_bytes": received})


@app.route('/api/uploads/<upload_id>/chunk', methods=['POST'])
def upload_chunk(upload_id):
    path = os.path.join(_uploads_dir(), f"{upload_id}.part")
    meta_path = os.path.join(_uploads_dir(), f"{upload_id}.json")
    if not os.path.exists(path) or not os.path.exists(meta_path):
        return jsonify({"success": False, "error": "上传不存在"}), 404

    chunk = request.files.get("chunk")
    if not chunk:
        return jsonify({"success": False, "error": "缺少 chunk"}), 400
    try:
        offset = int(request.form.get("offset") or 0)
    except Exception:
        offset = 0
    data = chunk.read()
    if not data:
        return jsonify({"success": False, "error": "空 chunk"}), 400

    with open(path, "r+b") as f:
        f.seek(offset)
        f.write(data)

    received = os.path.getsize(path)
    return jsonify({"success": True, "received_bytes": received})


@app.route('/api/uploads/<upload_id>/finalize', methods=['POST'])
def finalize_upload(upload_id):
    data = request.json or {}
    product_id = int(data.get("product_id") or 0)
    crop = data.get("crop")
    path = os.path.join(_uploads_dir(), f"{upload_id}.part")
    meta_path = os.path.join(_uploads_dir(), f"{upload_id}.json")
    if not product_id:
        return jsonify({"success": False, "error": "缺少 product_id"}), 400
    if not os.path.exists(path) or not os.path.exists(meta_path):
        return jsonify({"success": False, "error": "上传不存在"}), 404

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    expected = int(meta.get("size") or 0)
    actual = os.path.getsize(path)
    if expected and actual < expected:
        return jsonify({"success": False, "error": "上传未完成"}), 400
    if actual > 5 * 1024 * 1024:
        return jsonify({"success": False, "error": "图片超过 5MB 限制"}), 400

    with open(path, "rb") as f:
        raw = f.read()
    try:
        info = _store_image(product_id, raw, crop=crop if isinstance(crop, dict) else None)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    try:
        os.remove(path)
        os.remove(meta_path)
    except Exception:
        pass
    return jsonify({"success": True, "image": info})

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """获取分类和品牌元数据"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories WHERE level = 2")
    categories = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT id, name FROM brands")
    brands = [dict(row) for row in cursor.fetchall()]
    tags = _get_functional_tags(cursor)
    conn.close()
    return jsonify({
        'categories': categories,
        'brands': brands,
        'functional_tags': tags
    })


@app.route('/api/ai/status', methods=['GET'])
def get_ai_status():
    return jsonify({"enabled": is_ai_enabled()})


def _ai_generate_tags_core(item_id: int) -> Dict[str, Any]:
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                p.id,
                p.title,
                p.style,
                c.name as category,
                b.name as brand,
                s.color_name,
                s.size_name,
                s.seasons,
                s.tag_ids
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN product_skus s ON p.id = s.product_id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("衣物不存在")

        cursor.execute("SELECT id, name FROM functional_tags ORDER BY name")
        available_tags = [dict(r) for r in cursor.fetchall()]
        tag_name_to_id = {t["name"]: int(t["id"]) for t in available_tags}

        current = {
            "title": row["title"],
            "category": row["category"] or "",
            "brand": row["brand"] or "",
            "color": row["color_name"] or "",
            "size": row["size_name"] or "",
            "style": row["style"] or "休闲",
            "seasons": _parse_seasons(row["seasons"]),
            "tags": [],
        }
        tag_id_to_name = {v: k for k, v in tag_name_to_id.items()}
        for tid in _parse_tag_ids(row["tag_ids"]):
            name = tag_id_to_name.get(tid)
            if name:
                current["tags"].append(name)

        cfg = ai_settings.as_tag_config()
        ai_obj = generate_ai_tags(item=current, available_tags=available_tags, config=cfg)
        style = ai_obj.get("style")
        seasons = _parse_seasons(ai_obj.get("seasons"))
        tags = ai_obj.get("tags") or []
        tags = tags if isinstance(tags, list) else []
        tag_ids = [tag_name_to_id[t["name"]] for t in tags if isinstance(t, dict) and t.get("name") in tag_name_to_id]

        if style not in {"休闲", "商务", "运动", "正式"}:
            style = current["style"]
        if not seasons:
            seasons = current["seasons"] or ["春", "夏", "秋", "冬"]

        cursor.execute("UPDATE products SET style = ? WHERE id = ?", (style, item_id))
        cursor.execute(
            """
            UPDATE product_skus
            SET seasons = ?, tag_ids = ?
            WHERE product_id = ?
            """,
            (json.dumps(seasons, ensure_ascii=False), json.dumps(tag_ids, ensure_ascii=False), item_id),
        )
        conn.commit()

        return {"style": style, "seasons": seasons, "tags": tags}
    finally:
        conn.close()


@app.route('/api/wardrobe/<int:item_id>/ai-tags', methods=['POST'])
def ai_generate_tags(item_id):
    """为指定衣物生成标签/季节/风格（AI）"""
    try:
        res = _ai_generate_tags_core(item_id)
        return jsonify({"success": True, **res})
    except AIClientError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        msg = str(e) or "生成失败"
        code = 404 if msg == "衣物不存在" else 400
        return jsonify({"success": False, "error": msg}), code


@app.route('/api/ai/batch-tags', methods=['POST'])
def ai_batch_tags():
    data = request.json or {}
    item_ids = data.get("item_ids") or []
    item_ids = [int(x) for x in item_ids if str(x).isdigit()]
    if not item_ids:
        return jsonify({"success": False, "error": "缺少 item_ids"}), 400

    results = {"success": [], "failed": []}
    for item_id in item_ids:
        try:
            _ai_generate_tags_core(item_id)
            results["success"].append({"id": item_id})
        except Exception as e:
            results["failed"].append({"id": item_id, "error": str(e)})

    return jsonify({"success": True, "results": results})

if __name__ == '__main__':
    # 在容器中运行时需要监听 0.0.0.0 以允许外部访问
    app.run(host='0.0.0.0', port=5001, debug=False)
