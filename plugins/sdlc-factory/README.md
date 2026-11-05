# sdlc-factory

Usine du SDLC, côté **serveur** : agents `planner` (Opus), `implementer` (Sonnet), `reviewer-{correctness,security,simplicity}` (Sonnet), `retro` (Opus) ; orchestrateur `sdlc-run` ; `sdlc-retro` ; garde-fous ; unités systemd. Dépend de `sdlc-contract`. Parcours complet : [README racine](../../README.md#parcours-sdlc).

Expérimental : aucun appel réel de bout en bout n'a été vérifié (voir plus bas).

## Installation — serveur

**Pré-requis GitHub.** L'automate tourne sous un **compte distinct** (machine user, collaborateur en *écriture*, non admin). Avec ton propre jeton il serait admin, contournerait la protection de branche et rien ne le retiendrait. Toi, admin, pousses directement sur `main` (`enforce_admins: false`) ; le bot passe obligatoirement par PR + checks.

**Pré-requis système.** `python3`, `git`, `gh`, `claude` (connecté : `claude login` en tant que `sdlc`, ou `ANTHROPIC_API_KEY`), et pour le sandbox Linux **`bubblewrap` et `socat`** (`apt install bubblewrap socat`). Sans eux, les appels échouent (`failIfUnavailable: true`) : c'est voulu.

```bash
sudo useradd -m -s /bin/bash sdlc
sudo -u sdlc git clone --branch <tag> git@github.com:gaetanars/claude-plugins.git /opt/sdlc   # épingle un tag : rien ne change sans ton accord
sudo mkdir /etc/sdlc && sudo cp /opt/sdlc/plugins/sdlc-factory/deploy/env.example /etc/sdlc/env   # éditer, chmod 600, chown sdlc
printf 'toi/projet-a\n' | sudo tee /etc/sdlc/repos
sudo -u sdlc gh auth setup-git                       # credential helper git → GH_TOKEN
sudo cp /opt/sdlc/plugins/sdlc-factory/deploy/*.service /opt/sdlc/plugins/sdlc-factory/deploy/*.timer /etc/systemd/system/
sudo systemctl enable --now sdlc-run.timer sdlc-retro.timer
```

Le serveur utilise un **clone épinglé + `--plugin-dir`** (pas `claude plugin install`) : `sdlc-run` doit être appelable par un chemin stable depuis systemd, et la version déployée est un tag que tu choisis.

## Préparer un dépôt

```bash
sdlc-init-repo scaffold                                        # docs/, CLAUDE.md et .claude/check.json à renseigner
sdlc-init-repo github toi/projet-a --ci-context build          # dry-run : labels, settings, protection de branche
sdlc-init-repo github toi/projet-a --ci-context build --apply  # exécute (auto-merge désactivé)
```

- **Architecture** : `/sdlc-framing:architect init` sur le poste (ARCHITECTURE.md, `rules.json` neutre, configuration de l'outil natif du langage sous `docs/architecture/native/`, ADR), puis commit. `sdlc-publish` refuse sans architecture acceptée et commitée ; `sdlc-run` aussi (`needs-human`).
- **`.claude/check.json`** : `{"check": "<tests + lint + typecheck>", "arch": "<contrôle d'architecture>"}`, code de sortie 0 = vert. `sdlc-run` escalade en `needs-human` si l'un des deux est absent ou encore à `A_RENSEIGNER`.
- **Merge humain par défaut** : la PR est ouverte, `sdlc/verdicts` posé, l'issue passe à `in-review` ; tu fusionnes.
- **Auto-merge (opt-in par dépôt)** : `sdlc-init-repo github … --ci-context <ci> --automerge` (refusé sans `--ci-context`) **et** `toi/projet-a automerge` dans `/etc/sdlc/repos`. Le bot pose lui-même `sdlc/verdicts` : seule la CI du projet est un contrôle indépendant, d'où son caractère obligatoire.
- Protection de branche sur dépôt **privé** : plan GitHub payant requis. Sans elle, `sdlc/verdicts` ne peut pas être « requis ».

## Garde-fous

Trois couches, de la plus solide à la plus faible :

1. **Utilisateur Unix `sdlc`** (sans sudo, jeton GitHub limité aux dépôts concernés) : le vrai périmètre.
2. **Sandbox natif de Claude Code** (`--settings`) : activé et obligatoire (`failIfUnavailable`), pas d'échappatoire (`allowUnsandboxedCommands: false`), écriture limitée au worktree et au `.git` du clone de base, réseau limité à `SDLC_ALLOWED_DOMAINS` (défaut : `pypi.org,files.pythonhosted.org,registry.npmjs.org`). Il ne couvre que les commandes Bash.
3. **`scripts/guard.py`** (hook PreToolUse, déterministe, échec en **mode fermé** : toute exception refuse l'action ; `timeout` + `onFailure: block` dans `hooks.json`). Il refuse `git push`, `gh`, réseau direct, `sudo`, `rm` hors worktree, lecture/écriture hors worktree, secrets (`~/.ssh`, `~/.config/gh`…), et l'édition de `.github/`, `.claude/`, `docs/features/`, `docs/adr/` par l'implementer. Reviewers : seules les commandes `git` de lecture (aussi imposées par `--allowedTools` en motifs natifs).

Architecture verrouillée :
- `docs/architecture/` et `.claude/` sont refusés en écriture à l'implementer (`guard.py`) **et** contrôlés par l'orchestrateur sur le diff de chaque itération (`needs-human` si touchés) : le contrôle ne dépend pas du hook.
- Le planner ne tranche aucune décision de la liste « Exige un ADR » : elle remonte en `needs-clarification`. Seul l'humain change l'architecture (`architect revise`).
- Le SDLC ne contient aucun code par langage : l'outil natif est choisi au cadrage ; sans outil exploitable l'architecture reste `draft` et l'usine refuse de travailler.

Autres mesures :
- `--setting-sources user` : les hooks, `env` et `.mcp.json` du `.claude/settings.json` du dépôt cible sont ignorés (`CLAUDE.md` reste lu comme fichier). `--bare` n'est pas utilisé : il désactive les hooks du plugin.
- `--permission-mode dontAsk`, `--max-turns` par rôle (le `maxTurns` du frontmatter n'est pas documenté pour la session principale).
- L'agent ne voit jamais `GH_TOKEN`. `ANTHROPIC_API_KEY` reste visible de `claude` (il en a besoin) mais est retirée de l'environnement de `check`.
- La rétro ne peut pas modifier `scripts/ hooks/ bin/ lib/ deploy/ schemas/`, `plugins/sdlc-*/bin/`, `tests/`, `.claude-plugin/` ni `.github/` : le process évolue, pas sa sécurité. Elle bumpe le patch des `plugin.json` qu'elle modifie.

## Règles de verdict

`approve` ⇔ le relecteur approuve **et** aucun finding `blocker`/`major` (sinon requalifié en `changes_requested`, `adjusted: true`). Les revues ne sont lancées que si `check` et `arch`, exécutés par l'orchestrateur, sont verts ; un rouge renvoie sa sortie à l'implementer comme finding `blocker` (axes `check` et `arch`). Unanimité des 3 axes requise ; 3 itérations maximum (un `check` rouge compte), puis `needs-human`.

## Rodage

1. `sdlc-run --dry-run` (affiche l'issue retenue et le mode de merge).
2. Une petite feature réelle, merge humain, en lisant `docs/features/<id>/run.json` (tours, coûts, `subtype`, `permission_denials` par appel).
3. N'activer `automerge` sur un dépôt qu'après plusieurs runs propres et une CI solide.

## Vérifié / non vérifié

Vérifié (hors ligne) : `claude plugin validate --strict` ; orchestrateur de bout en bout contre un faux `gh`, un faux `claude` et un dépôt git local (nominal, rejet puis correction, escalade, clarification, dépendances, spec invalide, gates `check` et `arch` rouge puis vert / absents / au gabarit, architecture absente ou `draft`, modification de l'architecture par l'implementer, merge humain et opt-in, argv de `claude`) ; garde-fou (dont mode fermé et périmètre de la rétro) ; collecte de la rétro sur branches `feat/*`.

**Non vérifié** :
- Un vrai appel `claude -p --agent sdlc-factory:<agent> …` : les flags existent mais aucun modèle n'a été appelé, ni la prise en compte du hook du plugin en `-p`.
- Les outils natifs réels (génération de leur configuration par le skill `architect`, exécution de `arch`) dans chaque langage, et la qualité de l'entretien du skill : à juger à l'usage.
- Le sandbox réel (bubblewrap/socat sur le serveur Linux) et ses clés `sandbox.*` de `--settings` ; en particulier que `git commit` dans un worktree y fonctionne avec l'écriture sur le `.git` du clone de base.
- GitHub réel : protection de branche, auto-merge, statut `sdlc/verdicts`.
- Quotas : sur abonnement, Opus en boucle sera le premier goulot ; une clé API est l'alternative (`SDLC_BUDGET_USD` plafonne par appel).
