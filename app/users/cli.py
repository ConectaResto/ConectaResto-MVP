import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Rol, Usuario
from app.models.category import Category
from app.models.mesa import Mesa
from app.models.product import Product
from app.users.service import ensure_roles, get_rol_by_name, seed_demo


@click.command("init-roles")
@with_appcontext
def init_roles():
    """Crea los roles estándar si no existen: ADMIN, WAITER, KITCHEN, CASHIER."""
    ensure_roles()
    click.echo("Roles verificados: ADMIN, WAITER, KITCHEN, CASHIER")


@click.command("create-admin")
@click.option("--username", envvar="ADMIN_USERNAME", prompt="Usuario administrador")
@click.option("--email", envvar="ADMIN_EMAIL", prompt="Email del administrador")
@click.option(
    "--password",
    envvar="ADMIN_PASSWORD",
    prompt="Contraseña del administrador",
    hide_input=True,
    confirmation_prompt=True,
)
@with_appcontext
def create_admin(username, email, password):
    """Crea el primer usuario administrador sin credenciales hardcodeadas."""
    ensure_roles()
    existing_admin = (
        db.session.execute(
            db.select(Usuario).join(Rol).filter(Rol.name == "ADMIN", Usuario.is_active == True)
        )
        .scalars()
        .first()
    )
    if existing_admin:
        click.echo(f"Ya existe un administrador activo: {existing_admin.username}")
        return
    user = Usuario(username=username, email=email, rol_id=get_rol_by_name("ADMIN").id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Usuario administrador creado: {username}")


@click.command("seed-demo")
@click.option(
    "--password",
    envvar="SEED_PASSWORD",
    prompt="Contraseña para usuarios de demostración",
    hide_input=True,
    confirmation_prompt=True,
)
@with_appcontext
def seed_demo_cmd(password):
    """Crea datos de demostración: roles, usuarios, mesas, categorías y productos."""
    if not click.confirm("¿Está seguro de crear datos de demostración en esta base de datos?"):
        click.echo("Operación cancelada.")
        return
    seed_demo(password=password)
    click.echo("Datos de demostración creados exitosamente.")
