import matplotlib.pyplot as plt
import numpy as np


class Boiler:
    def __init__(self, puissance_nom, puissance_min, t_ext_base, t_ext_non_chauffage, t_min_chaudiere, t_max_chaudiere):
        self.puissance_nom = puissance_nom
        self.puissance_min = puissance_min
        self.t_ext_base = t_ext_base
        self.t_ext_non_chauffage = t_ext_non_chauffage
        self.t_min_chaudiere = t_min_chaudiere
        self.t_max_chaudiere = t_max_chaudiere
        self.pivot_t_ext = 20
        self.pivot_t_min = 20
        self.x = np.arange(self.t_ext_base, self.t_ext_non_chauffage + 1, 1)
        self.pente_temp_eau = 0
        self.depla_parallele = 0
        self.ordonnee_temp = 0
        self.y_temp_eau = 0
        self.pente_puissance = 0
        self.ordonnee_puissance = 0
        self.y_temp_pui = 0

    # Calculs des paramètres de la loi d'eau (pente et deplacement) : relation entre température extérieur et température de départ
    def loi_eau_t_depart_text(self):
        pente_temp_eau = (self.t_max_chaudiere - self.t_min_chaudiere) / (self.t_ext_base - self.t_ext_non_chauffage)
        depla_parallele = self.t_min_chaudiere - (self.pivot_t_min + ((self.pivot_t_ext - self.t_ext_non_chauffage) * -pente_temp_eau))
        # Calcul de l'ordonnée à l'origine (b) en utilisant l'équation de droite (Y = mX + b)
        ordonnee_origine = self.t_min_chaudiere - pente_temp_eau * self.t_ext_non_chauffage
        # Calcul des valeurs Y (température de l'eau) en utilisant l'équation de droite (Température d'eau)
        self.y_temp_eau = pente_temp_eau * self.x + ordonnee_origine  # équation a)
        self.pente_temp_eau = -pente_temp_eau
        self.depla_parallele = depla_parallele
        self.ordonnee_temp = ordonnee_origine
        return -pente_temp_eau, depla_parallele

    # Calculs des paramètres de la loi d'eau (pente et ordonnée à l'origine) : relation entre température extérieur et puissance
    # Hypothèse de linéarité dans l'évolution de la puissance pour l'estimation
    def loi_eau_t_ext_puissance(self):
        pente_p = (self.puissance_nom - self.puissance_min) / (self.t_ext_base - self.t_ext_non_chauffage)
        # Calcul de l'ordonnée à l'origine (b) en utilisant l'équation de droite (Y = mX + b)
        b_puissance = self.puissance_min - pente_p * self.t_ext_non_chauffage
        # Calcul des valeurs Y (puissance) en utilisant l'équation de droite (Puissance)
        # Calcul de l'ordonnée à l'origine (b) en utilisant l'équation de droite (Y = mX + b)
        ordonnee_origine = self.t_min_chaudiere - pente_p * self.t_ext_non_chauffage
        self.pente_puissance = pente_p
        self.ordonnee_puissance = b_puissance
        self.y_temp_pui = pente_p * self.x + b_puissance  # équation b)

    def tracer_graphique(self):  # Créer une figure 3D
        fig = plt.figure(figsize=(14, 7), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        # Tracer le graphique 3D
        ax.plot(self.x, self.y_temp_eau, self.y_temp_pui, label='Évolution de la puissance avec la température de l\'eau', color="crimson")

        ax.set_xlabel('Température extérieure (°C)')
        ax.set_ylabel('Température de l\'eau (°C)')
        ax.set_zlabel('Puissance')
        ax.invert_xaxis()
        ax.set_title('Évolution de la puissance et de la température de l\'eau en fonction de la température extérieure')
        plt.tight_layout()
        fig.savefig("figures/3D_Chaudiere")

        fig2 = plt.figure(2, figsize=(14, 7), dpi=100)
        plt.plot(self.x, self.y_temp_eau, label='Relation linéaire', color="crimson")
        plt.xlabel('Température extérieure (°C)')
        plt.gca().invert_xaxis()
        plt.ylabel('Température de l\'eau (°C)')
        plt.title('Relation entre température extérieure et température de départ de l\'eau')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.xticks(np.arange(self.t_ext_base, self.t_ext_non_chauffage + 1, 1))
        plt.yticks(np.arange(20, self.t_max_chaudiere + 1, 5))
        fig2.savefig("figures/Relation_Text_Tdépart")

        fig3 = plt.figure(3, figsize=(14, 7), dpi=100)
        plt.plot(self.x, self.y_temp_pui, label='Relation linéaire', color="crimson")
        plt.xlabel('Température extérieure (°C)')
        plt.gca().invert_xaxis()
        plt.ylabel('Puissance [kW]')
        plt.title('Relation entre température extérieure et Puissance')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.xticks(np.arange(self.t_ext_base, self.t_ext_non_chauffage + 1, 1))
        plt.yticks(np.arange(10, 65 + 1, 5))
        fig3.savefig("figures/Relation_Text_Puissance")

        fig4 = plt.figure(4, figsize=(14, 7), dpi=100)
        plt.plot(self.y_temp_eau, self.y_temp_pui, label='Relation linéaire', color="crimson")
        plt.xlabel('Température de départ (°C)')
        plt.ylabel('Puissance [kW]')
        plt.title('Relation entre température de départ et Puissance')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.xticks(np.arange(20, self.t_max_chaudiere + 1, 5))
        plt.yticks(np.arange(10, 65 + 1, 5))
        fig4.savefig("figures/Relation_Tdepart_Puissance")

    def calculer_puissance(self, temperature_depart_eau):
        puissance_calculee = self.pente_puissance * ((-self.ordonnee_temp + temperature_depart_eau) / -self.pente_temp_eau) + self.ordonnee_puissance  # trouvée à partir d'une résolution du système d'équation a) et b)
        return puissance_calculee

    def calculer_t_depart(self, temperature_ext):
        temp_depart = -self.pente_temp_eau * temperature_ext + self.ordonnee_temp
        if temp_depart > self.t_max_chaudiere:
            result = self.t_max_chaudiere
        elif temp_depart < self.t_min_chaudiere:
            result = self.t_min_chaudiere
        else:
            result = temp_depart
        return result
