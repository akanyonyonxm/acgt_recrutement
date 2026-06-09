"""Utilitaires partagés."""

import unicodedata


def normaliser_texte(texte: str) -> str:
    """Met un texte sous forme comparable : sans accents, minuscule, espaces simples.

    Sert à la recherche tolérante sur les noms (Kabamba / KABAMBA / Kabámba se
    ramènent tous à « kabamba »). Indépendant du SGBD : la normalisation est
    faite en amont, donc une simple recherche « contient » suffit, sur SQLite
    comme sur PostgreSQL.
    """
    if not texte:
        return ''
    # Décompose les caractères accentués puis retire les diacritiques.
    sans_accents = ''.join(
        c for c in unicodedata.normalize('NFKD', texte)
        if not unicodedata.combining(c)
    )
    return ' '.join(sans_accents.lower().split())


def tokens_recherche(requete: str) -> list[str]:
    """Découpe une requête en mots normalisés non vides."""
    return [t for t in normaliser_texte(requete).split() if t]
