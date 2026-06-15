"""All HTTP routes for SnapVault.

The handlers stay backend-agnostic: they talk to `repo` (DynamoDB or local
JSON) and `storage` (S3 or local filesystem), both resolved from the Flask
app config. CRUD lives here for two entities — albums and photos.
"""
import io

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from .config import Config
from .models import Album, Photo, normalize_tags

bp = Blueprint("main", __name__)


@bp.app_context_processor
def _inject_globals():
    # Available in every template: which backend is live (shown as a nav badge).
    return {"backend": current_app.config.get("BACKEND", "local")}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _repo():
    return current_app.config["REPO"]


def _storage():
    return current_app.config["STORAGE"]


def _album_or_404(album_id):
    album = _repo().albums.get(album_id)
    if album is None:
        abort(404)
    return album


def _photo_or_404(photo_id):
    photo = _repo().photos.get(photo_id)
    if photo is None:
        abort(404)
    return photo


def _photos_in(album_id):
    return _repo().photos.find_by("album_id", album_id)


def _album_name_map():
    return {a.id: a.name for a in _repo().albums.list()}


def _photos_grouped():
    """album_id -> [photos] (each list newest first, since list() is sorted)."""
    grouped = {}
    for p in _repo().photos.list():
        grouped.setdefault(p.album_id, []).append(p)
    return grouped


def _human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return ("%.0f %s" % (size, unit)) if unit == "B" else ("%.1f %s" % (size, unit))
        size /= 1024


def _ext_for(content_type):
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(content_type, "")


# --------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------
@bp.route("/")
def index():
    albums = _repo().albums.list()
    photos = _repo().photos.list()  # newest first
    favorites = [p for p in photos if p.is_favorite]

    # one pass over photos gives per-album counts and a cover (newest photo)
    counts, covers = {}, {}
    for p in photos:
        counts[p.album_id] = counts.get(p.album_id, 0) + 1
        covers.setdefault(p.album_id, p)

    stats = {
        "albums": len(albums),
        "photos": len(photos),
        "favorites": len(favorites),
        "storage": _human_size(sum(int(p.size or 0) for p in photos)),
    }
    cards = [
        {"album": a, "count": counts.get(a.id, 0), "cover": covers.get(a.id)}
        for a in albums[:6]
    ]

    return render_template(
        "dashboard.html",
        stats=stats,
        cards=cards,
        recent=photos[:8],
        favorites=favorites[:8],
        album_names={a.id: a.name for a in albums},
    )


# --------------------------------------------------------------------------
# albums  (CREATE / READ / UPDATE / DELETE)
# --------------------------------------------------------------------------
@bp.route("/albums", methods=["GET", "POST"])
def albums():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Album name is required.", "error")
        else:
            _repo().albums.save(Album.new(name))
            flash("Album created.", "ok")
        return redirect(url_for("main.albums"))

    grouped = _photos_grouped()
    albums = _repo().albums.list()
    cards = []
    for a in albums:
        ps = grouped.get(a.id, [])
        cards.append({"album": a, "count": len(ps), "cover": ps[0] if ps else None})
    return render_template("albums.html", cards=cards)


@bp.route("/albums/<album_id>")
def album_detail(album_id):
    album = _album_or_404(album_id)
    photos = _photos_in(album_id)
    return render_template("album.html", album=album, photos=photos)


@bp.route("/albums/<album_id>/rename", methods=["POST"])
def album_rename(album_id):
    album = _album_or_404(album_id)
    new_name = (request.form.get("name") or "").strip()
    if not new_name:
        flash("Album name is required.", "error")
    else:
        album.name = new_name
        _repo().albums.save(album)
        flash("Album renamed.", "ok")
    return redirect(url_for("main.album_detail", album_id=album_id))


@bp.route("/albums/<album_id>/delete", methods=["POST"])
def album_delete(album_id):
    album = _album_or_404(album_id)
    # cascade: remove every photo's S3 object and DynamoDB row first
    for photo in _photos_in(album_id):
        if photo.file_key:
            _storage().delete(photo.file_key)
        _repo().photos.delete(photo.id)
    _repo().albums.delete(album.id)
    flash("Album and its photos were deleted.", "ok")
    return redirect(url_for("main.albums"))


@bp.route("/albums/<album_id>/reshare", methods=["POST"])
def album_reshare(album_id):
    """Rotate the public share token (invalidates the old link)."""
    album = _album_or_404(album_id)
    album.share_token = Album.new("x").share_token
    _repo().albums.save(album)
    flash("New share link generated.", "ok")
    return redirect(url_for("main.album_detail", album_id=album_id))


# --------------------------------------------------------------------------
# photos  (CREATE / READ / UPDATE / DELETE)
# --------------------------------------------------------------------------
@bp.route("/albums/<album_id>/upload", methods=["GET", "POST"])
def upload(album_id):
    album = _album_or_404(album_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        tags = request.form.get("tags") or ""
        file = request.files.get("photo")

        if not title or file is None or file.filename == "":
            flash("A title and an image file are both required.", "error")
            return render_template("upload.html", album=album)

        if file.mimetype not in Config.ALLOWED_TYPES:
            flash("Only PNG, JPEG, WEBP or GIF images are allowed.", "error")
            return render_template("upload.html", album=album)

        data = file.read()  # read once so we know the size and can re-stream
        photo = Photo.new(album_id=album.id, title=title, description=description, tags=tags)

        safe_name = secure_filename(file.filename) or ("photo" + _ext_for(file.mimetype))
        key = "albums/%s/%s-%s" % (album.id, photo.id, safe_name)

        # UPLOAD: app writes the bytes to S3 (or local fs) itself
        _storage().save(key, io.BytesIO(data), file.mimetype)

        photo.file_key = key
        photo.file_name = safe_name
        photo.content_type = file.mimetype
        photo.size = str(len(data))
        _repo().photos.save(photo)

        flash("Photo uploaded.", "ok")
        return redirect(url_for("main.album_detail", album_id=album.id))

    return render_template("upload.html", album=album)


@bp.route("/photos/<photo_id>")
def photo_detail(photo_id):
    photo = _photo_or_404(photo_id)
    album = _repo().albums.get(photo.album_id)
    all_albums = _repo().albums.list()
    return render_template("photo.html", photo=photo, album=album, all_albums=all_albums)


@bp.route("/photos/<photo_id>/edit", methods=["POST"])
def photo_edit(photo_id):
    photo = _photo_or_404(photo_id)
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("main.photo_detail", photo_id=photo_id))

    photo.title = title
    photo.description = (request.form.get("description") or "").strip()
    photo.tags = normalize_tags(request.form.get("tags") or "")

    # optional: move the photo to another album
    new_album = (request.form.get("album_id") or "").strip()
    if new_album and _repo().albums.get(new_album) is not None:
        photo.album_id = new_album

    _repo().photos.save(photo)
    flash("Photo updated.", "ok")
    return redirect(url_for("main.photo_detail", photo_id=photo_id))


@bp.route("/photos/<photo_id>/favorite", methods=["POST"])
def photo_favorite(photo_id):
    photo = _photo_or_404(photo_id)
    photo.favorite = "0" if photo.is_favorite else "1"
    _repo().photos.save(photo)
    # bounce back to wherever the user clicked from
    return redirect(request.referrer or url_for("main.photo_detail", photo_id=photo_id))


@bp.route("/photos/<photo_id>/delete", methods=["POST"])
def photo_delete(photo_id):
    photo = _photo_or_404(photo_id)
    album_id = photo.album_id
    if photo.file_key:
        _storage().delete(photo.file_key)  # remove the S3 object
    _repo().photos.delete(photo.id)         # remove the DynamoDB row
    flash("Photo deleted.", "ok")
    return redirect(url_for("main.album_detail", album_id=album_id))


@bp.route("/photos/<photo_id>/raw")
def photo_raw(photo_id):
    """Stream the image inline. The app downloads it from S3 (get_object)."""
    photo = _photo_or_404(photo_id)
    if not photo.file_key:
        abort(404)
    data = _storage().open(photo.file_key)
    return Response(data, mimetype=photo.content_type or "application/octet-stream")


@bp.route("/photos/<photo_id>/download")
def photo_download(photo_id):
    """Same bytes, but forced as a file download (Content-Disposition)."""
    photo = _photo_or_404(photo_id)
    if not photo.file_key:
        abort(404)
    data = _storage().open(photo.file_key)
    filename = photo.file_name or (photo.title + _ext_for(photo.content_type))
    return Response(
        data,
        mimetype=photo.content_type or "application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )


# --------------------------------------------------------------------------
# search / favorites / public share
# --------------------------------------------------------------------------
@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    needle = q.lower()
    results = []
    if needle:
        for p in _repo().photos.list():
            haystack = " ".join([p.title, p.description, p.tags]).lower()
            if needle in haystack:
                results.append(p)
    return render_template(
        "search.html", q=q, results=results, album_names=_album_name_map()
    )


@bp.route("/favorites")
def favorites():
    photos = [p for p in _repo().photos.list() if p.is_favorite]
    return render_template(
        "favorites.html", photos=photos, album_names=_album_name_map()
    )


@bp.route("/share/<token>")
def share(token):
    matches = _repo().albums.find_by("share_token", token)
    if not matches:
        abort(404)
    album = matches[0]
    photos = _photos_in(album.id)
    return render_template("share.html", album=album, photos=photos)


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------
@bp.app_errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404
