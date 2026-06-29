with open("src/xtv_support/api/auth_webapp.py", "r") as f:
    auth_content = f.read()

auth_content = auth_content.replace('''if TYPE_CHECKING:  # pragma: no cover
    from fastapi import Request''', 'from fastapi import Request')

with open("src/xtv_support/api/auth_webapp.py", "w") as f:
    f.write(auth_content)
