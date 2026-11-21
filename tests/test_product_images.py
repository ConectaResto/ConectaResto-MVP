import os

import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage
from app import create_app
from app.extensions import db
from app.catalog.models import Category, Product
from app.catalog.service import (
    create_category,
    create_product,
    upload_product_image,
    delete_product_image,
    get_product_image_filename,
    ProductImageError,
)


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------- Helpers ----------

def csrf_token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, username, password):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf_token(client)},
    )


def _make_admin_user(app):
    with app.app_context():
        from app.users.models import Rol, Usuario
        for nombre in ["ADMIN", "WAITER"]:
            rol = Rol(name=nombre, description=f"Rol {nombre}")
            db.session.add(rol)
        db.session.commit()
        admin_rol = db.session.execute(
            db.select(Rol).filter_by(name="ADMIN")
        ).scalar_one()
        waiter_rol = db.session.execute(
            db.select(Rol).filter_by(name="WAITER")
        ).scalar_one()
        admin = Usuario(username="admin1", email="admin1@test.com", rol_id=admin_rol.id)
        admin.set_password("admin-pass")
        waiter = Usuario(username="mesero1", email="mesero1@test.com", rol_id=waiter_rol.id)
        waiter.set_password("waiter-pass")
        db.session.add(admin)
        db.session.add(waiter)
        db.session.commit()


def _create_product(app, name="Producto Test", price="10.00"):
    with app.app_context():
        categoria = create_category({"name": "Bebidas", "description": "Refrescos"})
        product = create_product({
            "name": name,
            "description": "Desc",
            "price": price,
            "categoria_id": categoria.id,
        })
        return product.id


def _make_file_storage(data, name, content_type="image/jpeg"):
    return FileStorage(
        stream=__import__("io").BytesIO(data),
        filename=name,
        content_type=content_type,
    )


_JPEG_DATA = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
_PNG_DATA = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\tIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d-\x24\xd4\x00\x00\x00\x00IEND\xaeB`\x82"
)
_LARGE_DATA = b"\x00" * (3 * 1024 * 1024)  # 3 MiB
_BAD_DATA = b"not an image"
_HTML_DATA = b"<html><body>fake image</body></html>"


# ---------- Service layer tests ----------

def test_upload_and_delete_product_image_service(app):
    """Upload and delete image via service layer."""
    with app.app_context():
        product_id = _create_product(app)
        upload_dir = os.path.join(app.instance_path, "uploads", "products")

        # Upload JPEG
        file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
        product, cleanup = upload_product_image(product_id, file_storage)
        assert product.image_filename is not None
        assert product.image_filename.endswith(".jpg")
        assert get_product_image_filename(product_id) == product.image_filename

        # File should exist on disk
        new_path = os.path.join(upload_dir, product.image_filename)
        assert os.path.exists(new_path)

        # Old file should NOT be deleted before commit (cleanup info returned)
        assert cleanup["old_filename"] is None
        assert cleanup["new_path"] == new_path

        db.session.commit()

        # Delete image
        product, cleanup = delete_product_image(product_id)
        assert product.image_filename is None
        assert get_product_image_filename(product_id) is None
        # File should still exist (not deleted before commit)
        assert os.path.exists(new_path)
        assert cleanup["old_filename"] is not None

        db.session.commit()
        # After commit, file should be deleted (simulating route handler cleanup)
        if cleanup["old_filename"]:
            old_path = os.path.join(upload_dir, cleanup["old_filename"])
            if os.path.exists(old_path):
                os.remove(old_path)
        assert not os.path.exists(new_path)


def test_upload_png_service(app):
    """Upload PNG via service layer."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_PNG_DATA, "test.png", "image/png")
        product, cleanup = upload_product_image(product_id, file_storage)
        assert product.image_filename is not None
        assert product.image_filename.endswith(".png")
        db.session.commit()


def test_upload_invalid_extension_service(app):
    """Reject non-image extension via service layer."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_BAD_DATA, "bad.txt", "text/plain")
        with pytest.raises(ProductImageError):
            upload_product_image(product_id, file_storage)


def test_upload_nonexistent_product_service(app):
    """Upload to nonexistent product raises error."""
    with app.app_context():
        file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
        with pytest.raises(ProductImageError):
            upload_product_image(99999, file_storage)


def test_replace_image_service(app):
    """Replace image: old file kept until commit, then removed."""
    with app.app_context():
        product_id = _create_product(app)
        upload_dir = os.path.join(app.instance_path, "uploads", "products")

        # First upload
        file_storage1 = _make_file_storage(_JPEG_DATA, "test.jpg")
        product, cleanup1 = upload_product_image(product_id, file_storage1)
        old_filename = product.image_filename
        old_path = os.path.join(upload_dir, old_filename)
        assert os.path.exists(old_path)
        db.session.commit()

        # Replace with PNG
        file_storage2 = _make_file_storage(_PNG_DATA, "test.png", "image/png")
        product, cleanup2 = upload_product_image(product_id, file_storage2)
        assert product.image_filename != old_filename
        assert product.image_filename.endswith(".png")
        # Old file still exists (not deleted before commit)
        assert os.path.exists(old_path)
        # New file exists
        new_path = os.path.join(upload_dir, product.image_filename)
        assert os.path.exists(new_path)
        # Cleanup info has old filename for post-commit deletion
        assert cleanup2["old_filename"] == old_filename
        assert cleanup2["new_path"] == new_path

        db.session.commit()
        # After commit, old file removed (simulating route handler cleanup)
        if cleanup2["old_filename"]:
            old_path2 = os.path.join(upload_dir, cleanup2["old_filename"])
            if os.path.exists(old_path2):
                os.remove(old_path2)
        assert not os.path.exists(old_path)
        # New file still exists
        assert os.path.exists(new_path)


def test_delete_nonexistent_image_service(app):
    """Delete image from product without image is a no-op."""
    with app.app_context():
        product_id = _create_product(app)
        product, cleanup = delete_product_image(product_id)
        assert product.image_filename is None
        assert cleanup["old_filename"] is None


# ---------- Endpoint-level tests ----------

def test_upload_image_requires_auth(client, app):
    _make_admin_user(app)
    token = csrf_token(client)
    resp = client.put(
        "/products/1/image",
        data={"image": (FileStorage(stream=__import__("io").BytesIO(_JPEG_DATA), filename="x.jpg"), "x.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_upload_image_requires_admin(client, app):
    _make_admin_user(app)
    login(client, "mesero1", "waiter-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 403


def test_upload_image_requires_csrf(client, app):
    _make_admin_user(app)
    login(client, "admin1", "admin-pass")
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_image_success(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["image_filename"] is not None
    assert data["data"]["image_filename"].endswith(".jpg")


def test_upload_png_success(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_PNG_DATA, "test.png", "image/png")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200


def test_upload_image_no_file_field(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    resp = client.put(
        "/products/1/image",
        data={},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_image_bad_format(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_BAD_DATA, "bad.txt", "text/plain")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "bad.txt")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_image_too_large(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_LARGE_DATA, "large.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "large.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_image_nonexistent_product(client, app):
    _make_admin_user(app)
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/99999/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404


def test_delete_image_requires_auth(client, app):
    _make_admin_user(app)
    token = csrf_token(client)
    resp = client.delete(
        "/products/1/image",
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 401


def test_delete_image_requires_admin(client, app):
    _make_admin_user(app)
    login(client, "mesero1", "waiter-pass")
    token = csrf_token(client)
    resp = client.delete(
        "/products/1/image",
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 403


def test_delete_image_success(client, app):
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload first
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    # Delete
    resp = client.delete(
        "/products/1/image",
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data"]["image_filename"] is None


def test_delete_image_nonexistent_product(client, app):
    _make_admin_user(app)
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)
    resp = client.delete("/products/99999/image", headers={"X-CSRF-Token": token})
    assert resp.status_code == 404


def test_get_image_product_without_image(client, app):
    _create_product(app, "Producto Test", "10.00")
    resp = client.get("/products/1/image")
    assert resp.status_code == 404


def test_get_image_nonexistent_product(client, app):
    resp = client.get("/products/99999/image")
    assert resp.status_code == 404


def test_product_to_dict_includes_image_url(app):
    """to_dict includes image_url: null when no image, URL when image set."""
    with app.app_context():
        product_id = _create_product(app)
        product = db.session.get(Product, product_id)
        d = product.to_dict()
        assert d["image_url"] is None

        # Upload image
        file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
        upload_product_image(product_id, file_storage)
        db.session.commit()
        product = db.session.get(Product, product_id)
        d = product.to_dict()
        assert d["image_url"] == f"/products/{product_id}/image"


def test_image_persistence_on_product_update(client, app):
    """Image filename persists when product is updated via PATCH."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload image
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    # Update product
    resp = client.patch(
        "/products/1",
        json={"name": "Nuevo Nombre"},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data"]["image_url"] is not None


def test_image_persistence_on_product_deactivation(client, app):
    """Image persists when product is deactivated."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload image
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    # Deactivate product
    resp = client.delete("/products/1", headers={"X-CSRF-Token": token})
    assert resp.status_code == 200

    # Image filename still present in DB
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename is not None
        assert product.is_active is False


# ---------- Content-Type tests ----------

def test_get_image_jpeg_content_type(client, app):
    """GET image returns image/jpeg for JPEG files."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    resp = client.get("/products/1/image")
    assert resp.status_code == 200
    assert resp.content_type == "image/jpeg"


def test_get_image_png_content_type(client, app):
    """GET image returns image/png for PNG files."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    file_storage = _make_file_storage(_PNG_DATA, "test.png", "image/png")
    client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    resp = client.get("/products/1/image")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"


# ---------- Commit failure tests ----------

def test_upload_image_commit_failure_cleans_orphan(client, app):
    """Si falla el commit, el archivo nuevo se elimina y el anterior se conserva."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload first image successfully
    file_storage1 = _make_file_storage(_JPEG_DATA, "old.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage1, "old.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    old_filename = resp.get_json()["data"]["image_filename"]
    old_path = os.path.join(app.instance_path, "uploads", "products", old_filename)
    assert os.path.exists(old_path)

    # Make commit fail on next operation
    def failing_commit():
        raise ProductImageError("Commit simulado fallido")

    with patch.object(db.session, "commit", failing_commit):
        file_storage2 = _make_file_storage(_PNG_DATA, "new.png", "image/png")
        resp = client.put(
            "/products/1/image",
            data={"image": (file_storage2, "new.png")},
            headers={"X-CSRF-Token": token},
            content_type="multipart/form-data",
        )

    # Should return 400 (ProductImageError from commit failure)
    assert resp.status_code == 400

    # Old file should still exist (not deleted because commit failed)
    assert os.path.exists(old_path)

    # New file should have been cleaned up (orphan)
    new_filename = resp.get_json().get("data", {}).get("image_filename")
    if new_filename:
        new_path = os.path.join(app.instance_path, "uploads", "products", new_filename)
        assert not os.path.exists(new_path)

    # DB should still reference the old filename
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename == old_filename


def test_delete_image_commit_failure_keeps_file(client, app):
    """Si falla el commit al eliminar, el archivo permanece en disco."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload image first
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    filename = resp.get_json()["data"]["image_filename"]
    file_path = os.path.join(app.instance_path, "uploads", "products", filename)
    assert os.path.exists(file_path)

    # Make commit fail on delete
    def failing_commit():
        raise ProductImageError("Commit simulado fallido")

    with patch.object(db.session, "commit", failing_commit):
        resp = client.delete(
            "/products/1/image",
            headers={"X-CSRF-Token": token},
        )

    # Should return 404 (delete route returns 404 for ProductImageError)
    assert resp.status_code == 404

    # File should still exist (not deleted because commit failed)
    assert os.path.exists(file_path)

    # DB should still reference the filename
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename == filename


# ---------- SQLAlchemy commit failure tests ----------

def test_upload_image_sqlalchemy_commit_failure(client, app):
    """Si falla el commit con SQLAlchemyError, se limpia el archivo nuevo y se conserva el anterior."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Limpieza de archivos residuales de pruebas previas
    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    for f in os.listdir(upload_dir):
        try:
            os.remove(os.path.join(upload_dir, f))
        except OSError:
            pass

    # Upload first image successfully
    file_storage1 = _make_file_storage(_JPEG_DATA, "old.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage1, "old.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    old_filename = resp.get_json()["data"]["image_filename"]
    old_path = os.path.join(app.instance_path, "uploads", "products", old_filename)
    assert os.path.exists(old_path)

    # Make commit fail with SQLAlchemyError
    def failing_commit():
        raise SQLAlchemyError("Commit simulado fallido")

    with patch.object(db.session, "commit", failing_commit):
        file_storage2 = _make_file_storage(_PNG_DATA, "new.png", "image/png")
        resp = client.put(
            "/products/1/image",
            data={"image": (file_storage2, "new.png")},
            headers={"X-CSRF-Token": token},
            content_type="multipart/form-data",
        )

    # Should return 500 (SQLAlchemyError)
    assert resp.status_code == 500

    # Old file should still exist (not deleted because commit failed)
    assert os.path.exists(old_path)

    # New file should have been cleaned up (orphan): no extra files besides old_filename
    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    remaining = os.listdir(upload_dir)
    assert remaining == [old_filename]

    # DB should still reference the old filename
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename == old_filename


def test_delete_image_sqlalchemy_commit_failure(client, app):
    """Si falla el commit con SQLAlchemyError al eliminar, el archivo permanece en disco."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Upload image first
    file_storage = _make_file_storage(_JPEG_DATA, "test.jpg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "test.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    filename = resp.get_json()["data"]["image_filename"]
    file_path = os.path.join(app.instance_path, "uploads", "products", filename)
    assert os.path.exists(file_path)

    # Make commit fail with SQLAlchemyError on delete
    def failing_commit():
        raise SQLAlchemyError("Commit simulado fallido")

    with patch.object(db.session, "commit", failing_commit):
        resp = client.delete(
            "/products/1/image",
            headers={"X-CSRF-Token": token},
        )

    # Should return 500 (SQLAlchemyError)
    assert resp.status_code == 500

    # File should still exist (not deleted because commit failed)
    assert os.path.exists(file_path)

    # DB should still reference the filename
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename == filename


# ---------- Content validation tests ----------

def test_upload_html_renamed_to_jpg_service(app):
    """Rechazar archivo HTML con extension .jpg."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_HTML_DATA, "falso.jpg", "image/jpeg")
        with pytest.raises(ProductImageError) as exc:
            upload_product_image(product_id, file_storage)
        assert "no coincide con una imagen JPEG" in str(exc.value)


def test_upload_html_renamed_to_png_service(app):
    """Rechazar archivo HTML con extension .png."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_HTML_DATA, "falso.png", "image/png")
        with pytest.raises(ProductImageError) as exc:
            upload_product_image(product_id, file_storage)
        assert "no coincide con una imagen PNG" in str(exc.value)


def test_upload_incompatible_header_jpg_extension_service(app):
    """Rechazar cabecera PNG con extension .jpg."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_PNG_DATA, "falso.jpg", "image/jpeg")
        with pytest.raises(ProductImageError) as exc:
            upload_product_image(product_id, file_storage)
        assert "no coincide con una imagen JPEG" in str(exc.value)


def test_upload_incompatible_header_png_extension_service(app):
    """Rechazar cabecera JPEG con extension .png."""
    with app.app_context():
        product_id = _create_product(app)
        file_storage = _make_file_storage(_JPEG_DATA, "falso.png", "image/png")
        with pytest.raises(ProductImageError) as exc:
            upload_product_image(product_id, file_storage)
        assert "no coincide con una imagen PNG" in str(exc.value)


def test_upload_html_renamed_to_jpg_endpoint(client, app):
    """Endpoint rechaza HTML renombrado a .jpg."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Limpieza de archivos residuales de pruebas previas
    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    for f in os.listdir(upload_dir):
        try:
            os.remove(os.path.join(upload_dir, f))
        except OSError:
            pass

    file_storage = _make_file_storage(_HTML_DATA, "falso.jpg", "image/jpeg")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "falso.jpg")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False

    # No archivo guardado ni imagen_filename cambiado
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename is None

    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    assert len(os.listdir(upload_dir)) == 0


def test_upload_html_renamed_to_png_endpoint(client, app):
    """Endpoint rechaza HTML renombrado a .png."""
    _make_admin_user(app)
    _create_product(app, "Producto Test", "10.00")
    login(client, "admin1", "admin-pass")
    token = csrf_token(client)

    # Limpieza de archivos residuales de pruebas previas
    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    for f in os.listdir(upload_dir):
        try:
            os.remove(os.path.join(upload_dir, f))
        except OSError:
            pass

    file_storage = _make_file_storage(_HTML_DATA, "falso.png", "image/png")
    resp = client.put(
        "/products/1/image",
        data={"image": (file_storage, "falso.png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400

    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.image_filename is None

    upload_dir = os.path.join(app.instance_path, "uploads", "products")
    assert len(os.listdir(upload_dir)) == 0
