import sqlite3
import pandas as pd
import os

class SQLiteCache:
    """
    Gestionnaire de cache local pour les données de marché Cassandre.
    Utilise SQLite pour stocker les DataFrames Pandas.
    """
    def __init__(self, db_path: str = "data/cassandre_market_data.db"):
        self.db_path = db_path
        # S'assurer que le dossier existe
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
    def _get_table_name(self, ticker: str, interval: str) -> str:
        # Remplacer les caractères non valides pour les noms de table SQLite
        clean_ticker = ticker.replace("-", "_").replace(".", "_")
        return f"market_{clean_ticker}_{interval}"

    def load(self, ticker: str, interval: str) -> pd.DataFrame:
        """Charge les données depuis le cache s'il existe."""
        table_name = self._get_table_name(ticker, interval)
        if not os.path.exists(self.db_path):
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Vérifier si la table existe
                cursor = conn.cursor()
                cursor.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if cursor.fetchone()[0] == 0:
                    return None
                    
                # Lire les données
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn, index_col="Date")
                # S'assurer que l'index est bien en datetime (pour compatibilité avec la suite)
                df.index = pd.to_datetime(df.index)
                return df
        except Exception as e:
            print(f"⚠️ [Cache SQLite] Erreur lors de la lecture de {table_name}: {e}")
            return None

    def save(self, df: pd.DataFrame, ticker: str, interval: str):
        """Sauvegarde les données dans le cache SQLite (écrase les anciennes données pour ce MVP)."""
        table_name = self._get_table_name(ticker, interval)
        try:
            with sqlite3.connect(self.db_path) as conn:
                # pandas to_sql gère toute la création de la table 
                df.to_sql(table_name, conn, if_exists="replace", index=True, index_label="Date")
        except Exception as e:
            print(f"⚠️ [Cache SQLite] Erreur lors de l'écriture de {table_name}: {e}")
