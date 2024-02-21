# ---------------- CONSTANTES ----------------------
C = 4.18  # Capacité thermique massique l'eau


# -------------------------------------------------------------------------
class Radiateur:
    def __init__(self, puissance_nominale, temperature_ambiante, t_entree_dim, t_sortie_dim):
        self.puissance_nominale = puissance_nominale
        self.t_entree_radiateur = t_entree_dim
        self.t_sortie_radiateur = t_sortie_dim
        self.t_ambiante = temperature_ambiante
        self.t_moy_radiateur = (self.t_entree_radiateur + self.t_sortie_radiateur) / 2
        self.coefficient_rayonnement = 10
        self.surface_chauffe = self.puissance_nominale / ((self.t_moy_radiateur - self.t_ambiante) * self.coefficient_rayonnement)
        self.debit_radiateur_nom = (self.puissance_nominale / 1000) / ((self.t_entree_radiateur - self.t_sortie_radiateur) * C)

    # ------------------------ CALCUL PUISSANCE EN FONCTION DU REGIME DE T° ----------------------------
    def calcul_puissance(self, t_entree, t_sortie):
        t_moyenne = (t_entree + t_sortie) / 2
        puissance = self.surface_chauffe * (t_moyenne - self.t_ambiante) * self.coefficient_rayonnement
        return puissance
