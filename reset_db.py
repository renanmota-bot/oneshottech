import os
import glob
import django

# 1. Apaga o banco de dados antigo
if os.path.exists("db.sqlite3"):
    try:
        os.remove("db.sqlite3")
        print("🗑️ db.sqlite3 removido.")
    except Exception as e:
        print(f"⚠️ Não foi possível remover db.sqlite3: {e}")

# 2. Apaga apenas os arquivos de migração antigos sem excluir a pasta
migrations_files = glob.glob("core/migrations/00*.py")
for f in migrations_files:
    try:
        os.remove(f)
        print(f"🗑️ Migração removida: {f}")
    except Exception as e:
        print(f"⚠️ Erro ao remover {f}: {e}")

# 3. Garante que o diretório e __init__.py existam
os.makedirs("core/migrations", exist_ok=True)
init_py = os.path.join("core", "migrations", "__init__.py")
if not os.path.exists(init_py):
    with open(init_py, "w") as f:
        pass

# 4. Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from core.models import Usuario, Empresa

print("⚙️ Criando novas migrações...")
call_command('makemigrations', 'core')
call_command('migrate')

print("👤 Criando Usuário Super Admin (renan / 1234)...")
if not Usuario.objects.filter(username='renan').exists():
    user = Usuario.objects.create_superuser(
        username='renan',
        email='renan@oneshottech.com',
        password='1234',
        first_name='Renan',
        perfil='SUPER_ADMIN'
    )
    print("✅ Super Admin 'renan' criado com sucesso!")

print("🏢 Criando Empresa Inicial de Teste...")
empresa = Empresa.objects.create(
    nome='Produtora One Shot Tech',
    cnpj='00.000.000/0001-00',
    status='ATIVO',
    plano='MENSAL',
    valor_plano=150.00
)
print(f"✅ Empresa '{empresa.nome}' criada com sucesso!")

print("\n🚀 PROCESSO CONCLUÍDO! Rode o comando: python manage.py runserver")
