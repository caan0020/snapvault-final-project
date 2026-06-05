from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from .models import Album, Photo, db
from .storage import get_storage


main_bp = Blueprint("main", __name__)


def _owned_album_or_404(album_id: int) -> Album:
    album = db.session.get(Album, album_id)
    if album is None or album.owner_id != current_user.id:
        abort(404)
    return album


def _owned_photo_or_404(photo_id: int) -> Photo:
    photo = db.session.get(Photo, photo_id)
    if photo is None or photo.album.owner_id != current_user.id:
        abort(404)
    return photo


def _allowed(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/albums", methods=["GET", "POST"])
@login_required
def albums():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Album name is required.", "error")
        else:
            db.session.add(Album(name=name, owner_id=current_user.id))
            db.session.commit()
            flash("Album created.", "success")
        return redirect(url_for("main.albums"))

    return render_template("albums.html", albums=current_user.albums)


@main_bp.route("/albums/<int:album_id>")
@login_required
def album_detail(album_id: int):
    album = _owned_album_or_404(album_id)
    storage = get_storage()
    photos = [(p, storage.get_url(p.storage_key)) for p in album.photos]
    return render_template("album.html", album=album, photos=photos)


@main_bp.route("/albums/<int:album_id>/rename", methods=["POST"])
@login_required
def album_rename(album_id: int):
    album = _owned_album_or_404(album_id)
    new_name = (request.form.get("name") or "").strip()
    if not new_name:
        flash("Album name is required.", "error")
    else:
        album.name = new_name
        db.session.commit()
        flash("Album renamed.", "success")
    return redirect(url_for("main.album_detail", album_id=album_id))


@main_bp.route("/albums/<int:album_id>/delete", methods=["POST"])
@login_required
def album_delete(album_id: int):
    album = _owned_album_or_404(album_id)
    storage = get_storage()
    for photo in list(album.photos):
        storage.delete(photo.storage_key)
    db.session.delete(album)
    db.session.commit()
    flash("Album deleted.", "success")
    return redirect(url_for("main.albums"))


@main_bp.route("/albums/<int:album_id>/upload", methods=["GET", "POST"])
@login_required
def upload(album_id: int):
    album = _owned_album_or_404(album_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        file = request.files.get("file")

        if not title or file is None or file.filename == "":
            flash("Title and file are required.", "error")
            return render_template("upload.html", album=album)

        if not _allowed(file.filename):
            flash("Unsupported file type.", "error")
            return render_template("upload.html", album=album)

        storage = get_storage()
        key = storage.save(
            file.stream,
            file.filename,
            file.content_type or "application/octet-stream",
        )

        photo = Photo(
            title=title,
            description=description,
            storage_key=key,
            content_type=file.content_type or "application/octet-stream",
            album_id=album.id,
        )
        db.session.add(photo)
        db.session.commit()

        flash("Photo uploaded.", "success")
        return redirect(url_for("main.album_detail", album_id=album.id))

    return render_template("upload.html", album=album)


@main_bp.route("/photos/<int:photo_id>")
@login_required
def photo_detail(photo_id: int):
    photo = _owned_photo_or_404(photo_id)
    url = get_storage().get_url(photo.storage_key)
    return render_template("photo.html", photo=photo, url=url)


@main_bp.route("/photos/<int:photo_id>/edit", methods=["POST"])
@login_required
def photo_edit(photo_id: int):
    photo = _owned_photo_or_404(photo_id)
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not title:
        flash("Title is required.", "error")
    else:
        photo.title = title
        photo.description = description
        db.session.commit()
        flash("Photo updated.", "success")
    return redirect(url_for("main.photo_detail", photo_id=photo_id))


@main_bp.route("/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def photo_delete(photo_id: int):
    photo = _owned_photo_or_404(photo_id)
    album_id = photo.album_id
    get_storage().delete(photo.storage_key)
    db.session.delete(photo)
    db.session.commit()
    flash("Photo deleted.", "success")
    return redirect(url_for("main.album_detail", album_id=album_id))


@main_bp.route("/uploads/<path:key>")
@login_required
def serve_upload(key: str):
    return send_from_directory(current_app.config["LOCAL_UPLOAD_DIR"], key)
