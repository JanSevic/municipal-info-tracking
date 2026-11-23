"""Vygeneruje pár klíčů pro šifrování e-mailových adres odběratelů.

  python tools/generate_keys.py <soubor_pro_soukromy_klic>

Veřejný klíč se uloží do config/public_key.pem (patří do repozitáře).
Obsah soukromého klíče vložte do GitHub Secrets jako SUBSCRIPTIONS_PRIVATE_KEY
a soubor pak smažte. Bez něj nelze e-maily dešifrovat (a nikdo jiný také ne).
"""
import pathlib
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = pathlib.Path(__file__).resolve().parent.parent
key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
(ROOT / "config" / "public_key.pem").write_bytes(key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
pathlib.Path(sys.argv[1]).write_bytes(key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
print("Veřejný klíč: config/public_key.pem; soukromý klíč:", sys.argv[1])
