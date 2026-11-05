# sdlc-factory

Usine du SDLC, sur un **serveur Orca** : une automatisation Orca lance le skill `/sdlc-factory:deliver` dans un worktree neuf ;
il prend la prochaine issue `ready`, planifie (`planner`, Opus), implémente en TDD vérifié (`implementer`, Sonnet),
fait relire (`reviewer`, Sonnet, contexte vierge, trois axes) puis ouvre la PR. **Le merge est toujours humain.**
`sdlc-gate` porte tout ce qui doit être déterministe : choix de l'issue, validations, TDD, gates, verdict, push, PR, labels.
Dépend de `sdlc-contract`. Parcours complet : [README racine](../../README.md#parcours-sdlc).

## Déroulé d'un run

```
Orca (cron + precheck `sdlc-gate next`) → session Claude dans un worktree neuf → /sdlc-factory:deliver
  sdlc-gate start        issue ready la plus ancienne (dépendances fermées) → in-progress, branche feat/<id>,
                         spec inchangée depuis sa publication, spec + architecture + .claude/check.json valides
  planner                plan.md ; question bloquante → posée dans la session (réponse dans « Clarifications » du plan)
                         décision « Exige un ADR » → sdlc-gate escalate (needs-human)
  implementer            par étape : commit test → sdlc-gate tests-red (check rouge constaté) → commit feat → sdlc-gate verify
  sdlc-gate verify       check + arch verts, chemins protégés intacts, TDD respecté
  reviewer → sdlc-gate review   approve requalifié si blocker/major ; 3 refus → needs-human
  docs/learnings.md      apprentissages réutilisables du run
  sdlc-gate deliver      verdict approve sur le dernier code, verify, push feat/<id>, PR « Closes #n », issue in-review
```

Une seule issue `in-progress` à la fois par dépôt. Une question en attente laisse l'issue `in-progress` : réponds dans la session (desktop ou mobile Orca).

## Contrôles de `sdlc-gate`

- **TDD** : tout commit `test(...)` doit avoir été constaté rouge par `sdlc-gate tests-red` (note `refs/notes/sdlc-red`) ; tout commit `feat(...)` suit un commit `test` ;
  le commit qui suit un commit `test` ne modifie aucun de ses fichiers.
- **Chemins protégés** (diff depuis la base) : `docs/architecture/`, `docs/adr/`, `.claude/`, `.github/`, `spec.md` et `brief.md` de la feature.
- **Gates** : `check` et `arch` de `.claude/check.json`, exécutés par `sdlc-gate` lui-même (sans variables de jeton).
- **Verdict** : schéma `verdict.schema.json` de sdlc-contract, enregistré sur le commit relu (`refs/notes/sdlc-review`) ; après le verdict,
  seuls `docs/learnings.md` et `plan.md` peuvent encore changer.
- N'écrit jamais `.git/config` (protégé par la sandbox) : branches en `--no-track`, push sans `-u`.

## Installation du serveur

Prérequis : Orca (`orca serve service install`, appairé en Tailscale au desktop et au mobile), `git`, `gh`, `claude`, `python3`,
et pour le sandbox Linux `bubblewrap` et `socat`. Un utilisateur Unix dédié (ex. `dev`) fait tourner Orca ; ses `git`, clé SSH et `gh` sont ceux de l'usine.

1. **Plugins** : clone de la marketplace épinglé sur un tag, puis installation depuis ce chemin.
   ```bash
   git clone --branch <tag> git@github.com:gaetanars/claude-plugins.git ~/sdlc
   claude plugin marketplace add ~/sdlc
   claude plugin install sdlc-factory@gaetanars    # sdlc-contract suit en dépendance ; sdlc-framing pour cadrer sur le serveur
   ```
2. **Réglages Claude** (`/etc/claude-code/managed-settings.json` ou `~/.claude/settings.json`) : sandbox obligatoire, réseau sur liste blanche,
   clés lisibles mais non modifiables. Aucune règle `Read` ni `sandbox.credentials` sur `~/.ssh` et `~/.config/gh` : elles les masquent au sandbox
   et empêchent signature, push SSH et `gh`.
   ```json
   {
     "permissions": { "defaultMode": "auto", "deny": ["Edit(~/.ssh/**)", "Edit(~/.config/gh/**)", "Read(~/.claude.json)"] },
     "sandbox": {
       "enabled": true, "failIfUnavailable": true, "allowUnsandboxedCommands": false,
       "network": { "strictAllowlist": true, "allowedDomains": ["github.com", "*.github.com", "*.githubusercontent.com", "registry.npmjs.org"] }
     }
   }
   ```
   `gh auth status` doit indiquer un stockage fichier (`~/.config/gh/hosts.yml`) : le trousseau système n'est pas joignable depuis le sandbox.
   Si tes consignes personnelles (`CLAUDE.md`, règles du mode auto) interdisent push et PR sans accord, ajoute une exception limitée :
   *dans une session lancée par `/sdlc-factory:deliver`, pousser `feat/<id>` et ouvrir sa PR via `sdlc-gate deliver` est autorisé ; jamais de push sur la branche de base, jamais de merge.*
3. **Dépôt** : clone dédié à l'usine (remote SSH), enregistré dans Orca, puis une automatisation par dépôt.
   ```bash
   git clone git@github.com:OWNER/REPO.git ~/repos/REPO && orca repo add --path ~/repos/REPO
   orca automations create --name "sdlc REPO" --trigger hourly --enabled \
     --repo path:$HOME/repos/REPO --workspace-mode new-per-run --base-branch origin/main \
     --precheck "$HOME/sdlc/plugins/sdlc-factory/bin/sdlc-gate next --repo OWNER/REPO" \
     --provider claude --extra-agent-args="--model opus" --prompt "/sdlc-factory:deliver"
   ```

## Préparer un dépôt (sur le poste)

`sdlc-init-repo scaffold`, `/sdlc-framing:architect init`, renseigner `.claude/check.json` et `CLAUDE.md`, commiter ;
`sdlc-init-repo github OWNER/REPO --ci-context <ci> --apply` (labels, protection de branche, auto-merge désactivé).

## Risques assumés

L'usine agit avec l'identité GitHub de l'utilisateur du serveur. Si c'est ton compte (admin) : la protection de branche ne la retient pas
(`enforce_admins: false`), elle peut lire ta clé et ton jeton et pousser sur tous les dépôts que ta clé atteint, et ses commits portent ta signature.
Restent : le sandbox (réseau et écriture), `sdlc-gate` (qui ne pousse que `feat/<id>`), le footer `Feature: <id>` et ta relecture de chaque PR.
Un compte bot non admin réduit ce périmètre.

## Vérifié / non vérifié

Vérifié hors ligne (`tests/test_sdlc_gate.py`, faux `gh`, dépôts git locaux) : `next`, `start` (dont escalades), cycle TDD, `verify`, `review` (requalification, plafond),
`deliver`, `escalate`. Vérifié sur le serveur (essai Orca du 2026-11-05) : skill lancé depuis le prompt d'automatisation, worktree neuf par exécution,
commit signé, push SSH et `gh` depuis le sandbox, mode auto sans blocage, question posée dans la session.

**Non vérifié** : un run complet de `/sdlc-factory:deliver` (sous-agents, enchaînement, qualité du plan et de la revue), l'écriture des notes git
depuis le sandbox, la reprise d'une branche après `needs-human`, la réponse depuis le mobile, la consommation de quota.
