import pandas as pd
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

logger = logging.getLogger("CassandreAI")

class AIEngine:
    """
    Moteur d'Intelligence Artificielle de Cassandre.
    Utilise le Machine Learning pour prédire la probabilité de hausse du marché.
    S'appuie sur les indicateurs calculés par IndicatorEngine.
    """
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        self.is_trained = False
        self.feature_cols = []

    def prepare_data(self, df: pd.DataFrame, target_horizon: int = 5):
        """
        Prépare les features et le target pour l'entraînement.
        Les features sont déjà précalculées dans df par IndicatorEngine.
        Target: 1 si le prix à Close[i + target_horizon] > Close[i], sinon 0.
        """
        if df is None or len(df) < 50:
            return None, None

        # Copie pour calcul de la target
        data = df.copy()
        
        # 1. Target (Classification: 1 = UP, 0 = DOWN/STAGNANT)
        # On regarde si dans 'target_horizon' bougies le prix est supérieur au prix actuel
        data['Target'] = (data['Close'].shift(-target_horizon) > data['Close']).astype(int)
        
        # 2. Nettoyage des NaNs (causés par les fenêtres glissantes des indicateurs)
        data = data.dropna()
        
        if data.empty:
            return None, None

        # 3. Sélection des colonnes numériques pour les features
        # On exclut les colonnes de service et la target
        exclude = ['Target', 'OpenTime', 'Date', 'CloseTime', 'symbol']
        self.feature_cols = [c for c in data.columns if c not in exclude and data[c].dtype in [np.float64, np.int64, np.float32, np.int32]]
        
        X = data[self.feature_cols]
        y = data['Target']
        
        return X, y

    def train(self, df_history: pd.DataFrame):
        """
        Entraîne le modèle sur les données historiques fournies (contenant les indicateurs).
        """
        logger.info("🧠 [AI] Entraînement du modèle experte en cours...")
        X, y = self.prepare_data(df_history)
        
        if X is None or len(X) < 100:
            logger.warning("⚠️ [AI] Pas assez de données propres pour entraîner l'IA (requis >100 lignes après dropna).")
            return False

        try:
            # Split pour validation interne
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            self.model.fit(X_train, y_train)
            score = self.model.score(X_test, y_test)
            
            self.is_trained = True
            logger.info(f"✅ [AI] Modèle opérationnel. Précision validation: {score*100:.1f}%")
            return True
        except Exception as e:
            logger.error(f"❌ [AI] Échec de l'entraînement : {e}")
            return False

    def predict(self, current_slice: pd.DataFrame):
        """
        Prédit la probabilité de hausse pour la dernière ligne de données.
        Retourne (probabilité_up, signal_recommandé)
        """
        if not self.is_trained or not self.feature_cols:
            return 0.5, "HOLD"

        # On s'assure de n'utiliser que la dernière bougie pour la prédiction finale
        X_last = current_slice[self.feature_cols].tail(1)
        
        # Vérification si la dernière ligne contient des NaNs
        if X_last.isnull().values.any():
            return 0.5, "HOLD"

        try:
            # Probabilités pour [DOWN, UP]
            probs = self.model.predict_proba(X_last)[0]
            prob_up = probs[1]
            
            # Seuils de décision "Expert"
            if prob_up > 0.65:
                return prob_up, "BUY"
            elif prob_up < 0.35:
                return prob_up, "SELL"
            else:
                return prob_up, "HOLD"
        except Exception as e:
            logger.error(f"❌ [AI] Erreur de prédiction : {e}")
            return 0.5, "HOLD"
