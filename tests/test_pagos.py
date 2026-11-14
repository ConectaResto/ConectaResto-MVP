import pytest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.mesa import Mesa
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.rol import Rol
from app.models.servicio import Servicio
from app.models.usuario import Usuario


@pytest.fixture
def servicio(app):
    with app.app_context():
        mesa = Mesa(numero=1, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()

        rol = Rol(name="WAITER", description="Mesero de prueba")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="mesero_test",
            email="mesero_test@example.test",
            rol_id=rol.id,
        )
        usuario.set_password("test-password")
        db.session.add(usuario)
        db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id,
            abierto_por_id=usuario.id,
            estado="ACTIVO",
        )
        db.session.add(servicio)
        db.session.commit()
        yield servicio
        # Limpieza en orden inverso de dependencias
        db.session.query(Pago).delete()
        db.session.query(Pedido).delete()
        db.session.query(Servicio).delete()
        db.session.query(Usuario).delete()
        db.session.query(Rol).delete()
        db.session.query(Mesa).delete()
        db.session.commit()


def test_crear_pago_asociado_a_servicio(app, servicio):
    """Un pago puede crearse asociado a un servicio con importe y fecha de registro."""
    with app.app_context():
        # Reobtener el servicio dentro del contexto de esta sesión
        servicio = db.session.get(Servicio, servicio.id)

        registrado_por = db.session.query(Usuario).filter_by(
            username="mesero_test"
        ).one()

        pago = Pago(
            servicio_id=servicio.id,
            registrado_por_id=registrado_por.id,
            importe=Decimal("45.50"),
        )
        db.session.add(pago)
        db.session.commit()

        assert pago.id is not None
        assert pago.servicio_id == servicio.id
        assert pago.registrado_por_id == registrado_por.id
        assert pago.importe == Decimal("45.50")
        assert pago.fecha_registro is not None

        # Verificar relación bidireccional
        db.session.refresh(servicio)
        assert servicio.pago is not None
        assert servicio.pago.id == pago.id
        assert servicio.pago.importe == Decimal("45.50")
        assert servicio.pago.registrado_por_id == registrado_por.id


def test_un_servicio_no_puede_tener_dos_pagos(app, servicio):
    """Un servicio admite como máximo un pago registrado (unique constraint en servicio_id)."""
    with app.app_context():
        servicio = db.session.get(Servicio, servicio.id)

        registrado_por = db.session.query(Usuario).filter_by(
            username="mesero_test"
        ).one()

        pago1 = Pago(
            servicio_id=servicio.id,
            registrado_por_id=registrado_por.id,
            importe=Decimal("30.00"),
        )
        db.session.add(pago1)
        db.session.commit()

        # Intentar crear un segundo pago para el mismo servicio
        pago2 = Pago(
            servicio_id=servicio.id,
            registrado_por_id=registrado_por.id,
            importe=Decimal("20.00"),
        )
        db.session.add(pago2)
        try:
            db.session.commit()
            assert False, "Debería haberse rechazado el segundo pago"
        except Exception:
            db.session.rollback()

        # Verificar que solo existe un pago
        pagos = db.session.query(Pago).filter_by(servicio_id=servicio.id).all()
        assert len(pagos) == 1
        assert pagos[0].importe == Decimal("30.00")


def test_pago_requiere_servicio_existente(app, servicio):
    """No se puede crear un pago sin un servicio válido (FK constraint)."""
    with app.app_context():
        servicio = db.session.get(Servicio, servicio.id)
        registrado_por = db.session.query(Usuario).filter_by(
            username="mesero_test"
        ).one()

        pago = Pago(
            servicio_id=99999,
            registrado_por_id=registrado_por.id,
            importe=Decimal("10.00"),
        )
        db.session.add(pago)
        try:
            db.session.commit()
            assert False, "Debería haberse rechazado el pago con servicio inexistente"
        except Exception:
            db.session.rollback()


def test_importe_no_puede_ser_nulo(app, servicio):
    """El importe es obligatorio en un pago."""
    with app.app_context():
        servicio = db.session.get(Servicio, servicio.id)
        registrado_por = db.session.query(Usuario).filter_by(
            username="mesero_test"
        ).one()

        pago = Pago(
            servicio_id=servicio.id,
            registrado_por_id=registrado_por.id,
            importe=None,
        )
        db.session.add(pago)
        try:
            db.session.commit()
            assert False, "Debería haberse rechazado el pago sin importe"
        except Exception:
            db.session.rollback()


def test_importe_debe_ser_positivo(app, servicio):
    """El importe debe ser mayor a cero (CheckConstraint)."""
    with app.app_context():
        servicio = db.session.get(Servicio, servicio.id)
        registrado_por = db.session.query(Usuario).filter_by(
            username="mesero_test"
        ).one()

        pago = Pago(
            servicio_id=servicio.id,
            registrado_por_id=registrado_por.id,
            importe=Decimal("0.00"),
        )
        db.session.add(pago)
        try:
            db.session.commit()
            assert False, "Debería haberse rechazado el importe cero"
        except Exception:
            db.session.rollback()


def test_pago_requiere_registrado_por(app, servicio):
    """registrado_por_id es obligatorio en un pago."""
    with app.app_context():
        servicio = db.session.get(Servicio, servicio.id)

        pago = Pago(
            servicio_id=servicio.id,
            registrado_por_id=None,
            importe=Decimal("10.00"),
        )
        db.session.add(pago)
        try:
            db.session.commit()
            assert False, "Debería haberse rechazado el pago sin registrado_por_id"
        except Exception:
            db.session.rollback()