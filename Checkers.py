import pyxel
import os
import shutil

# --- Constantes ---
VIDE    = 0
PION_J1 = 1
PION_J2 = 2
DAME_J1 = 3
DAME_J2 = 4

PIONS_J1 = {PION_J1, DAME_J1}
PIONS_J2 = {PION_J2, DAME_J2}

DIAGONALE_DROITE     = (1, -1)
DIAGONALE_GAUCHE     = (-1, -1)
DIAGONALE_BAS_DROITE = (1,  1)
DIAGONALE_BAS_GAUCHE = (-1, 1)
DIAGONALES = [DIAGONALE_GAUCHE, DIAGONALE_DROITE, DIAGONALE_BAS_GAUCHE, DIAGONALE_BAS_DROITE]

DIRS_PION = {
    PION_J1: [(-1, -1), (1, -1)],
    PION_J2: [(-1,  1), (1,  1)],
}


def case_valide(x, y):
    return 0 <= x < 10 and 0 <= y < 10 and (x + y) % 2 == 1


class Game:

    # -------------------------------------------------------------------------
    # 1. INITIALISATION
    # -------------------------------------------------------------------------

    def __init__(self):
        self.plateau = self._init_plateau()
        self.tour = 1
        self.selection = None
        self.cases_jaunes = []
        self.doit_rejouer = False
        self.started = False
        self.game_mode = 0
        self.gagnant = None
        self.show_infos = False
        self.show_tick_sound = False
        self.show_tick_last_square = False
        self.show_tick_music = True
        self.menu_music_playing = False
        self.show_tick_yellow_points = False
        self.rafle_en_cours = False
        self.last_square = None
        self._must_jump_debut_tour = False
        self.show_tick_lvl_1 = False
        self.show_tick_lvl_2 = False
        self.show_tick_lvl_3 = False
        self.show_tick_lvl_4 = False
        self.profondeur = None
        self.image_chargee = False

        pyxel.init(160, 160, title="CHECKERS", fps=30)
        try:
            pyxel.load("res.pyxres")
        except FileNotFoundError:
            print("Avertissement : fichier res.pyxres introuvable.")

        pyxel.run(self.update, self.draw)

    def _init_plateau(self):
        plateau = [[VIDE] * 10 for _ in range(10)]
        for y in range(10):
            for x in range(10):
                if (x + y) % 2 == 1:
                    if y <= 3:
                        plateau[y][x] = PION_J2
                    elif y >= 6:
                        plateau[y][x] = PION_J1
        return plateau

    def _debut_tour(self):
        """À appeler au début de chaque tour pour figer must_jump."""
        self._must_jump_debut_tour = self.saut_obligatoire(plateau=self.plateau)

    def _reset(self):
        self.plateau = self._init_plateau()
        self.tour = 1
        self.selection = None
        self.cases_jaunes = []
        self.doit_rejouer = False
        self.started = False
        self.game_mode = 0
        self.gagnant = None
        self.show_infos = False
        self.show_tick_sound = False
        self.show_tick_last_square = False
        self.show_tick_music = True
        self.menu_music_playing = False
        self.show_tick_yellow_points = False
        self.rafle_en_cours = False
        self.last_square = None
        self._must_jump_debut_tour = False
        self.show_tick_lvl_1 = False
        self.show_tick_lvl_2 = False
        self.show_tick_lvl_3 = False
        self.show_tick_lvl_4 = False
        self.profondeur = None
        self.image_chargee = False

    # -------------------------------------------------------------------------
    # 2. HELPERS D'ÉTAT
    # -------------------------------------------------------------------------

    def _adversaires(self, valeur):
        return PIONS_J2 if valeur in PIONS_J1 else PIONS_J1

    def _est_mon_pion(self, valeur):
        if self.tour % 2 == 1:
            return valeur in PIONS_J1
        return valeur in PIONS_J2

    # -------------------------------------------------------------------------
    # 3. CALCUL DES MOUVEMENTS
    # -------------------------------------------------------------------------

    def _mouvements_pion(self, px, py, valeur, adversaires, must_jump, rafle_en_cours=None, plateau=None):
        if plateau is None:
            plateau = self.plateau
        if rafle_en_cours is None:
            rafle_en_cours = self.rafle_en_cours

        cases = []

        # Captures
        for dx, dy in DIRS_PION[valeur]:
            nx, ny = px + dx, py + dy
            nnx, nny = px + 2 * dx, py + 2 * dy

            # Captures vers l'avant
            if (case_valide(nx, ny) and case_valide(nnx, nny)
                    and plateau[ny][nx] in adversaires
                    and plateau[nny][nnx] == VIDE):
                cases.append((nnx, nny))

            # Captures vers l'arrière (autorisées si rafle_en_cours est True)
            if rafle_en_cours:
                nx, ny = px - dx, py - dy
                nnx, nny = px - 2 * dx, py - 2 * dy

                if (case_valide(nx, ny) and case_valide(nnx, nny)
                        and plateau[ny][nx] in adversaires
                        and plateau[nny][nnx] == VIDE):
                    cases.append((nnx, nny))

        # Déplacements simples (sans capture)
        if not must_jump:
            for dx, dy in DIRS_PION[valeur]:
                nx, ny = px + dx, py + dy
                if case_valide(nx, ny) and plateau[ny][nx] == VIDE:
                    cases.append((nx, ny))

        return cases

    def _mouvements_dame(self, px, py, adversaires, must_jump, plateau=None):
        if plateau is None:
            plateau = self.plateau

        cases = []
        for dx, dy in DIAGONALES:
            pion_saute = False
            for i in range(1, 10):
                nx, ny = px + dx * i, py + dy * i
                if not case_valide(nx, ny):
                    break
                if plateau[ny][nx] == VIDE:
                    if pion_saute or not must_jump:
                        cases.append((nx, ny))
                    if pion_saute:
                        break
                elif plateau[ny][nx] in adversaires and not pion_saute:
                    nnx, nny = nx + dx, ny + dy
                    if case_valide(nnx, nny) and plateau[nny][nnx] == VIDE:
                        pion_saute = True
                    else:
                        break
                else:
                    break
        return cases

    def _cases_jaunes_pour(self, px, py, valeur, force_saut=False, plateau=None):
        if plateau is None:
            plateau = self.plateau

        must_jump = force_saut or self._must_jump_debut_tour
        adversaires = self._adversaires(valeur)

        if valeur in {DAME_J1, DAME_J2}:
            cases = self._mouvements_dame(px, py, adversaires, must_jump, plateau=plateau)
        else:
            cases = self._mouvements_pion(px, py, valeur, adversaires, must_jump, plateau=plateau)

        if must_jump and plateau is self.plateau:
            max_longueur = 0
            longueurs = {}
            for (dest_x, dest_y) in cases:
                plateau_copie = [ligne[:] for ligne in plateau]
                plateau_copie[py][px] = VIDE

                # ── Trouver la vraie case capturée selon le type de pièce ──
                if valeur in {DAME_J1, DAME_J2}:
                    # Parcourir la diagonale pour trouver l'adversaire
                    dx = 1 if dest_x > px else -1
                    dy = 1 if dest_y > py else -1
                    cx, cy = px + dx, py + dy
                    cap_x, cap_y = None, None
                    while (cx, cy) != (dest_x, dest_y):
                        if plateau_copie[cy][cx] in adversaires:
                            cap_x, cap_y = cx, cy
                            break
                        cx += dx
                        cy += dy
                    if cap_x is None:
                        longueurs[(dest_x, dest_y)] = 1
                        continue
                else:
                    cap_x = (px + dest_x) // 2
                    cap_y = (py + dest_y) // 2

                # --- CORRECTION MODIFICATION NSI ---
                # On vide la case de départ et la case d'arrivée sur la copie
                plateau_copie[cap_y][cap_x] = VIDE
                plateau_copie[dest_y][dest_x] = valeur
                                
                # On passe cette liste à la fonction récursive (pensez à modifier la signature de _compter_captures_recursif pour l'accepter !)
                suite = self._compter_captures_recursif((dest_x, dest_y), valeur, plateau_copie)                
                total = 1 + suite
                longueurs[(dest_x, dest_y)] = total
                if total > max_longueur:
                    max_longueur = total

            cases = [(x, y) for (x, y), l in longueurs.items() if l == max_longueur]

        return cases

    def un_saut_possible(self, x, y, valeur):
        adversaires = self._adversaires(valeur)
        if valeur in {DAME_J1, DAME_J2}:
            return bool(self._mouvements_dame(x, y, adversaires, must_jump=True))
        else:
            return bool(self._mouvements_pion(x, y, valeur, adversaires, must_jump=True))

    def saut_obligatoire(self, plateau):
        pions_joueur = PIONS_J1 if self.tour % 2 == 1 else PIONS_J2
        for y in range(10):
            for x in range(10):
                if plateau[y][x] in pions_joueur:
                    if self.un_saut_possible(x, y, plateau[y][x]):
                        return True
        return False
    
    """MINIMAX"""

    def obtenir_tous_les_coups(self, plateau, joueur):
        coups = []
        pions_cibles = PIONS_J2 if joueur == 2 else PIONS_J1

        must_jump = self.saut_obligatoire(plateau)

        for y in range(10):
            for x in range(10):
                valeur = plateau[y][x]
                if valeur in pions_cibles:
                    # FIX : Passage des arguments nommés pour respecter la signature (force_saut, plateau)
                    destinations = self._cases_jaunes_pour(x, y, valeur, force_saut=must_jump, plateau=plateau)

                    for dest_x, dest_y in destinations:
                        coups.append(((x, y), (dest_x, dest_y)))
                        
        return coups

        
    def evaluer(self, plateau):
        score = 0
        
        nb_pions_j1, nb_dames_j1 = 0, 0
        nb_pions_j2, nb_dames_j2 = 0, 0

        for y in range(10):
            for x in range(10):
                v = plateau[y][x]
                if v == VIDE:
                    continue
                    
                if v == PION_J2:
                    nb_pions_j2 += 1
                    score += 100                 # Valeur de base du pion
                    score += y * 10              # Incitation forte à avancer (promotion)
                    if 2 <= x <= 7: score += 10  # Contrôle du centre
                    if x == 0 or x == 9: score += 15 # Protection des bords (incapturable !)
                    
                elif v == DAME_J2:
                    nb_dames_j2 += 1
                    score += 350                 # Une dame vaut 3.5 pions
                    if 3 <= x <= 6 and 3 <= y <= 6: score += 20 # Centralisation de la dame
                    
                elif v == PION_J1:
                    nb_pions_j1 += 1
                    score -= 100
                    score -= (9 - y) * 10
                    if 2 <= x <= 7: score -= 10
                    if x == 0 or x == 9: score -= 15
                    
                elif v == DAME_J1:
                    nb_dames_j1 += 1
                    score -= 350
                    if 3 <= x <= 6 and 3 <= y <= 6: score -= 20

        # États terminaux (Victoire / Défaite totale)
        if nb_pions_j2 == 0 and nb_dames_j2 == 0: return -100000 
        if nb_pions_j1 == 0 and nb_dames_j1 == 0: return 100000 

        return score

    def appliquer_coup_sim(self, plateau, coup):
        """Applique un coup sur un plateau simulé et retourne le nouveau plateau."""
        nouveau_plateau = [ligne[:] for ligne in plateau]
        (sx, sy), (dest_x, dest_y) = coup
        piece = nouveau_plateau[sy][sx]
        
        # Déplacement
        nouveau_plateau[sy][sx] = VIDE
        nouveau_plateau[dest_y][dest_x] = piece
        
        # Si c'est une capture, on supprime le pion mangé
        if abs(dest_x - sx) > 1:
            dx = 1 if dest_x > sx else -1
            dy = 1 if dest_y > sy else -1
            cx, cy = sx + dx, sy + dy
            while (cx, cy) != (dest_x, dest_y):
                nouveau_plateau[cy][cx] = VIDE
                cx += dx
                cy += dy
                
        # Promotion en dame simple
        if piece == PION_J1 and dest_y == 0:
            nouveau_plateau[dest_y][dest_x] = DAME_J1
        elif piece == PION_J2 and dest_y == 9:
            nouveau_plateau[dest_y][dest_x] = DAME_J2
            
        return nouveau_plateau

    def minimax(self, plateau, profondeur, alpha, beta, joueur_maximisant):
        """Algorithme Minimax avec élagage Alpha-Beta."""
        if profondeur == 0:
            return self.evaluer(plateau), None

        if joueur_maximisant: # Le bot (J2)
            max_eval = float('-inf')
            meilleur_coup = None
            coups = self.obtenir_tous_les_coups(plateau, 2)
            
            if not coups: return self.evaluer(plateau), None

            for coup in coups:
                plateau_sim = self.appliquer_coup_sim(plateau, coup)
                eval_courante, _ = self.minimax(plateau_sim, profondeur - 1, alpha, beta, False)
                
                if eval_courante > max_eval:
                    max_eval = eval_courante
                    meilleur_coup = coup
                
                alpha = max(alpha, eval_courante)
                if beta <= alpha:
                    break # Élagage
            return max_eval, meilleur_coup
            
        else: # L'humain (J1)
            min_eval = float('inf')
            pire_coup = None
            coups = self.obtenir_tous_les_coups(plateau, 1)
            
            if not coups: return self.evaluer(plateau), None

            for coup in coups:
                plateau_sim = self.appliquer_coup_sim(plateau, coup)
                eval_courante, _ = self.minimax(plateau_sim, profondeur - 1, alpha, beta, True)
                
                if eval_courante < min_eval:
                    min_eval = eval_courante
                    pire_coup = coup
                    
                beta = min(beta, eval_courante)
                if beta <= alpha:
                    break # Élagage
            return min_eval, pire_coup

    # ── LOGIQUE RÉCURSIVE POUR LA RAFLE MAXIMALE ─────────────────────────────

    def _compter_captures_recursif(self, position, valeur, plateau_sim):
        """Calcule la longueur maximale d'un chemin de captures sur un plateau simulé.
        Ne modifie jamais self.plateau ni aucun attribut de l'instance."""
        adversaires = self._adversaires(valeur)
        x, y = position
        # Calcul des sauts disponibles selon le type de pièce
        if valeur in {DAME_J1, DAME_J2}:
            sauts = []
            for dx, dy in DIAGONALES:
                pion_saute = False
                cx, cy = None, None
                for i in range(1, 10):
                    nx, ny = x + dx * i, y + dy * i
                    if not case_valide(nx, ny):
                        break
                    if plateau_sim[ny][nx] == VIDE:
                        if pion_saute:
                            sauts.append((nx, ny, cx, cy))
                            break
                    elif plateau_sim[ny][nx] in adversaires and not pion_saute:
                        nnx, nny = nx + dx, ny + dy
                        if case_valide(nnx, nny) and plateau_sim[nny][nnx] == VIDE:
                            pion_saute = True
                            cx, cy = nx, ny
                        else:
                            break
                    else:
                        break
        else:
            # FIX : On passe explicitement les arguments par mot-clé pour éviter le décalage
            sauts = self._mouvements_pion(x, y, valeur, adversaires, must_jump=True, rafle_en_cours=True, plateau=plateau_sim)

        # Cas de base : plus aucun saut possible
        if not sauts:
            return 0

        max_captures = 0

        if valeur in {DAME_J1, DAME_J2}:
            for (dest_x, dest_y, cap_x, cap_y) in sauts:
                plateau_copie = [ligne[:] for ligne in plateau_sim]
                plateau_copie[y][x] = VIDE
                plateau_copie[cap_y][cap_x] = VIDE
                plateau_copie[dest_y][dest_x] = valeur
                suite = self._compter_captures_recursif((dest_x, dest_y), valeur, plateau_copie)
                if 1 + suite > max_captures:
                    max_captures = 1 + suite
        else:
            for (dest_x, dest_y) in sauts:
                plateau_copie = [ligne[:] for ligne in plateau_sim]
                plateau_copie[y][x] = VIDE
                cap_x = (x + dest_x) // 2
                cap_y = (y + dest_y) // 2
                plateau_copie[cap_y][cap_x] = VIDE
                plateau_copie[dest_y][dest_x] = valeur
                suite = self._compter_captures_recursif((dest_x, dest_y), valeur, plateau_copie)
                if 1 + suite > max_captures:
                    max_captures = 1 + suite

        return max_captures

    def longueur_rafle(self, sx, sy):
        """Calcule la longueur de rafle maximale depuis (sx, sy).
        FIX : copie le vrai plateau ici pour que la simulation soit totalement isolée."""
        valeur = self.plateau[sy][sx]
        if valeur == VIDE:
            return 0
        plateau_copie = [ligne[:] for ligne in self.plateau]
        return self._compter_captures_recursif((sx, sy), valeur, plateau_copie)

    def is_rafle_plus_grande(self, sx, sy):
        """Vérifie si la pièce sélectionnée offre la rafle maximale parmi toutes les pièces du joueur."""
        score_candidat = self.longueur_rafle(sx, sy)

        pions_joueur = PIONS_J1 if self.tour % 2 == 1 else PIONS_J2
        max_tous_pions = 0

        for y in range(10):
            for x in range(10):
                if self.plateau[y][x] in pions_joueur:
                    score = self.longueur_rafle(x, y)
                    if score > max_tous_pions:
                        max_tous_pions = score

        return score_candidat >= max_tous_pions

    # -------------------------------------------------------------------------
    # 4. ACTION : DÉPLACEMENT ET FIN DE TOUR
    # -------------------------------------------------------------------------

    def deplacer_pion(self, dest_x, dest_y):
        sx, sy = self.selection
        pièce = self.plateau[sy][sx]

        if not self.rafle_en_cours:
            self.last_square = (sx, sy)

        # ── Détection de capture ──────────────────────────────────────────────
        if pièce in {DAME_J1, DAME_J2}:
            dx = 1 if dest_x > sx else -1
            dy = 1 if dest_y > sy else -1
            adversaires = self._adversaires(pièce)
            est_capture = False
            cx, cy = sx + dx, sy + dy
            while (cx, cy) != (dest_x, dest_y):
                if self.plateau[cy][cx] in adversaires:
                    est_capture = True
                    break
                cx += dx
                cy += dy
        else:
            est_capture = abs(dest_x - sx) > 1

        # ── Déplacement ──────────────────────────────────────────────────────
        self.plateau[sy][sx] = VIDE
        self.plateau[dest_y][dest_x] = pièce

        # ── Suppression de la pièce capturée ─────────────────────────────────
        if est_capture:
            dx = 1 if dest_x > sx else -1
            dy = 1 if dest_y > sy else -1
            cx, cy = sx + dx, sy + dy
            while (cx, cy) != (dest_x, dest_y):
                self.plateau[cy][cx] = VIDE
                cx += dx
                cy += dy

        # Note : On NE FAIT PLUS la promotion ici au milieu.

        nouveau_pion = self.plateau[dest_y][dest_x]

        # ── Si ce n'est pas une capture : le tour est fini, promotion possible ──
        if not est_capture:
            # Application de la promotion en fin de mouvement passif
            if nouveau_pion == PION_J1 and dest_y == 0:
                self.plateau[dest_y][dest_x] = DAME_J1
            elif nouveau_pion == PION_J2 and dest_y == 9:
                self.plateau[dest_y][dest_x] = DAME_J2

            self.selection = None
            self.cases_jaunes = []
            self.doit_rejouer = False
            self.rafle_en_cours = False
            if self.show_tick_sound:
                pyxel.play(0, 1)
            self.tour += 1
            self._debut_tour()
            self._verifier_fin()
            return

        # ── C'est une capture : on vérifie si la rafle continue (sans promotion) ──
        self.rafle_en_cours = True
        sauts_suivants = self._cases_jaunes_pour(dest_x, dest_y, nouveau_pion, force_saut=True)

        if sauts_suivants:
            # La rafle continue : le pion reste un pion (pas de promotion encore)
            self.doit_rejouer = True
            self.selection = (dest_x, dest_y)
            self.cases_jaunes = sauts_suivants
        else:
            # La rafle est FINIE : c'est maintenant qu'on valide la promotion !
            if nouveau_pion == PION_J1 and dest_y == 0:
                self.plateau[dest_y][dest_x] = DAME_J1
            elif nouveau_pion == PION_J2 and dest_y == 9:
                self.plateau[dest_y][dest_x] = DAME_J2

            self.rafle_en_cours = False
            self.doit_rejouer = False
            self.selection = None
            self.cases_jaunes = []
            if self.show_tick_sound:
                pyxel.play(0, 1)
            self.tour += 1
            self._debut_tour()
            self._verifier_fin()

    def _verifier_fin(self):
        joueur_actuel = self.tour % 2
        pions_joueur = PIONS_J1 if joueur_actuel == 1 else PIONS_J2

        pions_restants = [
            (x, y)
            for y in range(10)
            for x in range(10)
            if self.plateau[y][x] in pions_joueur
        ]
        if not pions_restants:
            self.gagnant = 2 if joueur_actuel == 1 else 1
            return

        peut_jouer = any(
            self._cases_jaunes_pour(x, y, self.plateau[y][x])
            for x, y in pions_restants)
        if not peut_jouer:
            self.gagnant = 2 if joueur_actuel == 1 else 1

    def afficher_image(self):
        if not self.image_chargee:
            nom_fichier = "troll.png"
            
            # --- CORRECTION DU REPERTOIRE DE TRAVAIL ---
            # Récupère le dossier où se trouve le script Checkers.py
            dossier_script = os.path.dirname(os.path.abspath(__file__))
            # Force Python à travailler dans ce dossier
            os.chdir(dossier_script)
            # On charge directement le fichier puisqu'il est déjà dans le dossier !
            pyxel.images[2].load(0, 0, nom_fichier)
            self.image_chargee = True

    # -------------------------------------------------------------------------
    # 5. BOUCLE DE JEU : UPDATE
    # -------------------------------------------------------------------------

    def touche_btn_play(self):
        pyxel.mouse(True)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if 110 <= mx <= 126 and 91 <= my <= 107:
            if self.profondeur is not None:
                self.started = True
                self._debut_tour()
                pyxel.stop()
                self.menu_music_playing = False
            else:
                self.afficher_image()  # seulement si pas de niveau choisi

    def update(self):
        pyxel.mouse(True)
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._reset()
            if self.show_tick_music:
                pyxel.play(0, 0, loop=True)
                self.menu_music_playing = True
            return

        if not self.started:
            if self.show_tick_music and not self.menu_music_playing:
                pyxel.play(0, 0, loop=True)
                self.menu_music_playing = True

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):

                # ── État 1 : panneau options ──────────────────────────────────
                if self.show_infos:
                    if 140 <= mx <= 156 and 140 <= my <= 156:
                        self.show_infos = False
                    elif 110 <= mx <= 126 and 30 <= my <= 46:
                        self.show_tick_sound = not self.show_tick_sound
                    elif 110 <= mx <= 126 and 45 <= my <= 61:
                        self.show_tick_last_square = not self.show_tick_last_square
                    elif 110 <= mx <= 126 and 60 <= my <= 76:
                        self.show_tick_music = not self.show_tick_music
                        if self.show_tick_music:
                            pyxel.play(0, 0, loop=True)
                            self.menu_music_playing = True
                        else:
                            pyxel.stop()
                            self.menu_music_playing = False
                    elif 110 <= mx <= 126 and 75 <= my <= 91:
                        self.show_tick_yellow_points = not self.show_tick_yellow_points

                # ── État 2 : choix du niveau bot ─────────────────────────────
                elif self.game_mode == 2:
                    if 110 <= mx <= 126 and 30 <= my <= 46:
                        self.profondeur = 1
                        self.show_tick_lvl_1, self.show_tick_lvl_2, self.show_tick_lvl_3, self.show_tick_lvl_4 = True, False, False, False
                    elif 110 <= mx <= 126 and 45 <= my <= 61:
                        self.profondeur = 2
                        self.show_tick_lvl_1, self.show_tick_lvl_2, self.show_tick_lvl_3, self.show_tick_lvl_4 = False, True, False, False
                    elif 110 <= mx <= 126 and 60 <= my <= 76:
                        self.profondeur = 3
                        self.show_tick_lvl_1, self.show_tick_lvl_2, self.show_tick_lvl_3, self.show_tick_lvl_4 = False, False, True, False
                    elif 110 <= mx <= 126 and 75 <= my <= 91:
                        self.profondeur = 4
                        self.show_tick_lvl_1, self.show_tick_lvl_2, self.show_tick_lvl_3, self.show_tick_lvl_4 = False, False, False, True
                    else:
                        self.touche_btn_play()
                        return
                    
                # ── État 3 : menu principal ───────────────────────────────────
                else:
                    if 140 <= mx <= 156 and 140 <= my <= 156:
                        self.show_infos = True
                    elif 40 <= mx <= 120 and 50 <= my <= 80:
                        self.started, self.game_mode = True, 1
                        self._debut_tour()
                        pyxel.stop()
                        self.menu_music_playing = False
                    elif 40 <= mx <= 120 and 90 <= my <= 120:
                        self.game_mode = 2          # affiche le choix de niveau, ne démarre pas
            return

        if self.game_mode == 2 and self.tour % 2 == 0:
            self._jouer_bot()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            rotation = (self.game_mode == 1 and self.tour % 2 == 0)
            cx = (159 - mx) // 16 if rotation else mx // 16
            cy = (159 - my) // 16 if rotation else my // 16

            if not case_valide(cx, cy):
                return

            if (cx, cy) in self.cases_jaunes:
                self.deplacer_pion(cx, cy)
            elif not self.doit_rejouer and self.plateau[cy][cx] != VIDE:
                valeur = self.plateau[cy][cx]
                if self._est_mon_pion(valeur):
                    # Vérifie que ce pion a la rafle maximale globale
                    if self._must_jump_debut_tour and not self.is_rafle_plus_grande(cx, cy):
                        return
                    self.selection = (cx, cy)
                    self.cases_jaunes = self._cases_jaunes_pour(cx, cy, valeur)
            else:
                if not self.doit_rejouer:
                    self.cases_jaunes = []
                    self.selection = None

    def _jouer_bot(self):
        # Rafle en cours : self.cases_jaunes contient déjà les meilleures suites
        if self.doit_rejouer:
            if self.cases_jaunes:
                dest_x, dest_y = self.cases_jaunes[0]
                self.deplacer_pion(dest_x, dest_y)
                if self.show_tick_sound:
                    pyxel.play(0, 1)
            return

        # Tour normal : Minimax
        _, meilleur_coup = self.minimax(
            self.plateau, self.profondeur,
            float('-inf'), float('inf'),
            joueur_maximisant=True
        )
        if meilleur_coup:
            (sx, sy), (dest_x, dest_y) = meilleur_coup
            self.selection = (sx, sy)
            self.deplacer_pion(dest_x, dest_y)
            if self.show_tick_sound:
                pyxel.play(0, 1)

    # -------------------------------------------------------------------------
    # 6. RENDU : DRAW
    # -------------------------------------------------------------------------

    def draw(self):
        pyxel.cls(0)
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if not self.started:
            if self.show_infos:
                self._draw_infos()
                self._draw_out()
            else:
                self._draw_menu(mx, my)
                if self.game_mode == 2:
                    self._draw_choose_lvl()

        elif self.gagnant is not None:
            self._draw_fin()
        else:
            self._draw_plateau()

        # ← TOUJOURS EN DERNIER pour ne pas être écrasé par pyxel.cls(0)
        if self.image_chargee:
            pyxel.cls(0)
            pyxel.blt(55, 60, 2, 0, 0, 50, 50, 0)
            pyxel.text(40, 100, "What did you want to do ?", 7)
            pyxel.text(40, 110, "Press SPACE", 7)

    def _draw_menu(self, mx, my):
        pyxel.text(60, 20, "CHECKERS", 7)

        survol_solo = 40 <= mx <= 120 and 50 <= my <= 80
        pyxel.rect(40, 50, 80, 30, 10 if survol_solo else 7)
        if survol_solo:
            pyxel.text(30, 62, ">", 11)
        pyxel.text(55, 62, "SOLO (2P)", 0)

        survol_bot = 40 <= mx <= 120 and 90 <= my <= 120
        pyxel.rect(40, 90, 80, 30, 10 if survol_bot else 7)
        if survol_bot:
            pyxel.text(30, 102, ">", 11)
        pyxel.text(60, 102, "VS BOT", 0)

        pyxel.blt(140, 140, 1, 0, 32, 16, 16)

    def _draw_choose_lvl(self):
        if self.game_mode == 2:
            pyxel.cls(0)
            pyxel.rect(30, 30, 100, 100, 1)
            pyxel.text(30, 20, "Choose the level of the bot", 7)
            pyxel.text(40, 35, "1", 7)
            pyxel.text(40, 50, "2", 7)
            pyxel.text(40, 65, "3", 7)
            pyxel.text(40, 80, "4", 7)
            pyxel.blt(110, 30, 1,  0, 48, 16, 16)
            pyxel.blt(110, 45, 1,  0, 48, 16, 16)
            pyxel.blt(110, 60, 1,  0, 48, 16, 16)
            pyxel.blt(110, 75, 1,  0, 48, 16, 16)

            #bouton play - if not préssé le joueur choisi le lvl de difficulté du bot et peux le modifier tant que pas cliqué sur play
            pyxel.blt(110, 91, 1,  16, 64, 16, 16)
            
            if self.show_tick_lvl_1:
                pyxel.blt(110, 30, 1,  0, 64, 16, 16)
            if self.show_tick_lvl_2:
                pyxel.blt(110, 45, 1,  0, 64, 16, 16)
            if self.show_tick_lvl_3:
                pyxel.blt(110, 60, 1,  0, 64, 16, 16)
            if self.show_tick_lvl_4:
                pyxel.blt(110, 75, 1,  0, 64, 16, 16)

    def _draw_infos(self):
        pyxel.cls(0)
        pyxel.rect(30, 30, 100, 100, 1)
        pyxel.text(40, 35, "Sound", 7)
        pyxel.text(40, 50, "Last square", 7)
        pyxel.text(40, 65, "Music", 7)
        pyxel.text(40, 80, "Yellow points", 7)
        pyxel.blt(110, 30, 1,  0, 48, 16, 16)
        pyxel.blt(110, 45, 1,  0, 48, 16, 16)
        pyxel.blt(110, 60, 1,  0, 48, 16, 16)
        pyxel.blt(110, 75, 1,  0, 48, 16, 16)
        if self.show_tick_sound:
            pyxel.blt(110, 30, 1,  0, 64, 16, 16)
        if self.show_tick_last_square:
            pyxel.blt(110, 45, 1,  0, 64, 16, 16)
        if self.show_tick_music:
            pyxel.blt(110, 60, 1,  0, 64, 16, 16)
        if self.show_tick_yellow_points:
            pyxel.blt(110, 75, 1,  0, 64, 16, 16)

    def _draw_out(self):
        pyxel.blt(140, 140, 1, 16, 32, 16, 16)

    def _draw_plateau(self):
        rotation = (self.game_mode == 1 and self.tour % 2 == 0)
        pyxel.bltm(0, 0, 0, 0, 0, 160, 160)

        for y in range(10):
            for x in range(10):
                v = self.plateau[y][x]
                if v == VIDE:
                    continue
                dx = (9 - x) * 16 if rotation else x * 16
                dy = (9 - y) * 16 if rotation else y * 16
                if v == PION_J2:   pyxel.blt(dx, dy, 1,  0,  0, 16, 16)
                elif v == PION_J1: pyxel.blt(dx, dy, 1,  0, 16, 16, 16)
                elif v == DAME_J1: pyxel.blt(dx, dy, 1, 16, 16, 16, 16)
                elif v == DAME_J2: pyxel.blt(dx, dy, 1, 16,  0, 16, 16)

        if self.show_tick_last_square and self.last_square is not None:
            lx, ly = self.last_square
            dx = (9 - lx) * 16 if rotation else lx * 16
            dy = (9 - ly) * 16 if rotation else ly * 16
            pyxel.blt(dx, dy, 1, 16, 48, 16, 16)

        if self.show_tick_yellow_points:
            for jx, jy in self.cases_jaunes:
                dx = (9 - jx) * 16 if rotation else jx * 16
                dy = (9 - jy) * 16 if rotation else jy * 16
                pyxel.blt(dx, dy, 1, 32, 0, 16, 16)

    def _draw_fin(self):
        msg = f"PLAYER {self.gagnant} WIN !"
        x = 70 - len(msg)
        pyxel.text(x, 70, msg, 10)
        pyxel.text(15, 90, "Press SPACE to go back to the menu", 7)


Game()