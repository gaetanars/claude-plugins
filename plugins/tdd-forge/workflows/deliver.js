export const meta = {
  name: 'deliver',
  description: 'Livre en autonomie et en TDD les tâches cadrées par le PO et approuvées (forge.py approve) : plan, tests rouges, vert, refactor, revue, apprentissages, PR, merge si CI verte. Argument : { tasks: ["T001", ...] }.',
  phases: [
    { title: 'Préparation' },
    { title: 'Plan' },
    { title: 'Rouge' },
    { title: 'Vert' },
    { title: 'Refactor' },
    { title: 'Revue' },
    { title: 'Apprentissage' },
    { title: 'Livraison' },
  ],
}

// Tout état durable vit dans .forge/backlog/<T>/ (state.json, journal.jsonl), écrit par forge.py.
// Une relance, même dans une nouvelle session, reprend à l'étape renvoyée par `forge.py status`.

const FORGE = 'python3 .forge/bin/forge.py'
const STEPS = ['start', 'plan', 'red', 'green', 'refactor', 'review', 'learn', 'ship', 'wait']
const MAX_FIXES = 5 // corrections successives de l'implémenteur par contrôle vert
const MAX_REVIEW_ROUNDS = 3
const STDOUT = {
  type: 'object',
  required: ['stdout'],
  properties: { stdout: { type: 'string', description: 'Sortie standard brute de la commande.' } },
}

const header = (t) => [
  `Tâche ${t}.`,
  `Worktree : .forge/worktrees/${t}. Toute commande shell s'exécute en un seul appel : cd .forge/worktrees/${t} && <commande>.`,
  `Dossier de tâche : .forge/backlog/${t} (spec.md approuvée et figée, plan.md, revues, dispositions).`,
  `Apprentissages du projet : .forge/worktrees/${t}/.forge/learnings.md.`,
].join('\n')

const clip = (o) => JSON.stringify(o).slice(0, 6000)

async function forge(cmd, label) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const r = await agent(`${FORGE} ${cmd}`, { agentType: 'tdd-forge:runner', label, schema: STDOUT })
    if (r === null) return { error: `exécution interrompue (${label})` }
    try {
      return JSON.parse(r.stdout)
    } catch {
      // sortie retouchée par l'exécutant : une seconde tentative
    }
  }
  return { error: `sortie illisible (${label})` }
}

async function work(role, t, label, instructions) {
  const r = await agent(`${header(t)}\n\n${instructions}`, { agentType: `tdd-forge:${role}`, label })
  return r !== null
}

async function block(t, reason, detail) {
  log(`${t} bloquée : ${reason}`)
  const s = await forge(`ship ${t} --blocked "${reason.replace(/"/g, "'")}"`, `${t} · PR brouillon`)
  return { task: t, status: 'blocked', reason, pr: s.pr || null, detail: detail ? clip(detail).slice(0, 1500) : undefined }
}

async function greenLoop(t, phase, instructions) {
  let g = await forge(`green ${t} --phase ${phase}`, `${t} · contrôle ${phase}`)
  for (let fixes = 0; !g.error && !g.passed && !g.blocked; fixes++) {
    if (fixes >= MAX_FIXES) return { ...g, blocked: true, error: `plafond de ${MAX_FIXES} corrections atteint (${phase})` }
    const ok = await work('implementer', t, `${t} · ${phase}`,
      `${instructions}\n\nRésultat du dernier contrôle :\n${clip(g)}`)
    if (!ok) return { error: 'implémenteur interrompu' }
    g = await forge(`green ${t} --phase ${phase}`, `${t} · contrôle ${phase}`)
  }
  return g
}

async function deliverTask(t) {
  phase('Préparation')
  const s = await forge(`status ${t}`, `${t} · état`)
  if (s.error) return { task: t, status: 'error', reason: s.error }
  if (['invalid', 'done', 'blocked'].includes(s.next)) return { task: t, status: s.next, reason: s.reason, pr: s.pr }
  const todo = (step) => STEPS.indexOf(s.next) <= STEPS.indexOf(step)
  const stopped = { task: t, status: 'interrupted', reason: 'agent arrêté : relance le workflow pour reprendre' }

  if (todo('start')) {
    const r = await forge(`start ${t}`, `${t} · worktree`)
    if (r.error || !r.ok) return { task: t, status: 'error', reason: r.error || r.reason }
  }

  if (todo('plan')) {
    phase('Plan')
    if (!await work('planner', t, `${t} · plan`, 'Écris plan.md pour cette tâche.')) return stopped
  }

  if (todo('red')) {
    phase('Rouge')
    let instr = 'Phase rouge : écris le test d\'acceptation (un cas par AC-n, lié à son AC de façon visible dans les résultats de test) puis les autres tests prévus au plan. Ils doivent échouer pour la bonne raison.'
    for (;;) {
      if (!await work('test-writer', t, `${t} · tests rouges`, instr)) return stopped
      const r = await forge(`red ${t}`, `${t} · contrôle rouge`)
      if (r.error) return await block(t, 'Erreur technique en phase rouge', r)
      if (r.ok) break
      if (r.blocked) return await block(t, 'Phase rouge sans progrès', r)
      instr = `Phase rouge refusée par le contrôle. Corrige :\n${clip(r)}`
    }
  }

  if (todo('green')) {
    phase('Vert')
    const g = await greenLoop(t, 'impl', 'Phase verte : écris le code minimal qui fait passer tous les tests et les portes. Chaque AC-n doit apparaître dans les résultats de test, au vert.')
    if (!g.passed) return await block(t, g.error || 'Implémentation sans progrès', g)
  }

  if (todo('refactor')) {
    phase('Refactor')
    if (!await work('implementer', t, `${t} · refactor`, 'Phase refactor : améliore le design sans changer le comportement, tests au vert.')) return stopped
    const g = await greenLoop(t, 'refactor', 'Le refactor a cassé une porte : rétablis le vert sans changer le comportement.')
    if (!g.passed) return await block(t, g.error || 'Refactor sans retour au vert', g)
  }

  if (todo('review')) {
    phase('Revue')
    let round = s.review_round || 0
    for (;;) {
      round++
      if (round > MAX_REVIEW_ROUNDS) return await block(t, `Plafond de ${MAX_REVIEW_ROUNDS} tours de revue atteint`)
      if (!await work('reviewer', t, `${t} · revue ${round}`, `Revue, tour ${round}. Écris review-${round}.json.`)) return stopped
      const v = await forge(`review ${t} ${round}`, `${t} · verdict ${round}`)
      if (v.error) return await block(t, 'Revue illisible', v)
      if (v.approved) break
      if (v.blocked) return await block(t, 'Revue sans progrès sur les points bloquants', v)
      if (v.items_tests > 0) {
        if (!await work('test-writer', t, `${t} · tests revue ${round}`, `Mode revue, tour ${round} : traite les éléments target tests.`)) return stopped
        const u = await forge(`tests-update ${t}`, `${t} · tests revue`)
        if (u.error) return await block(t, 'Erreur sur les tests de revue', u)
      }
      if (v.items_code > 0) {
        if (!await work('implementer', t, `${t} · code revue ${round}`, `Mode revue, tour ${round} : traite les éléments target code.`)) return stopped
      }
      let d = await forge(`dispositions ${t} ${round}`, `${t} · dispositions ${round}`)
      if (!d.error && !d.ok) {
        const missing = `Éléments sans disposition valide :\n${clip(d)}`
        if (d.missing.tests.length || d.invalid.tests.length) await work('test-writer', t, `${t} · relance tests`, `Mode revue, tour ${round}. ${missing}`)
        if (d.missing.code.length || d.invalid.code.length) await work('implementer', t, `${t} · relance code`, `Mode revue, tour ${round}. ${missing}`)
        d = await forge(`dispositions ${t} ${round}`, `${t} · dispositions ${round}`)
      }
      if (d.error || !d.ok) return await block(t, 'Remarques de revue non traitées', d)
      const g = await greenLoop(t, 'review', 'Après les corrections de revue, une porte est rouge : rétablis le vert.')
      if (!g.passed) return await block(t, g.error || 'Corrections de revue sans retour au vert', g)
      if (v.blocking === 0) break // seules des remarques mineures : traitées, pas de nouveau tour
    }
  }

  if (todo('learn')) {
    phase('Apprentissage')
    if (!await work('learner', t, `${t} · apprentissages`, 'Rédige report.md et mets à jour learnings.md.')) return stopped
    await forge(`mark ${t} learned`, `${t} · apprentissage noté`)
  }

  phase('Livraison')
  if (todo('ship')) {
    const r = await forge(`ship ${t}`, `${t} · PR`)
    if (r.error) return { task: t, status: 'error', reason: r.error }
    if (!r.ok) return await block(t, r.reason || 'Contrôle final rouge', r)
    log(`${t} : PR ouverte ${r.pr}`)
  }
  for (;;) {
    const w = await forge(`wait-merge ${t}`, `${t} · CI et merge`)
    if (w.error) return { task: t, status: 'error', reason: w.error }
    if (w.state === 'merged') return { task: t, status: 'done', pr: w.pr }
    if (w.state !== 'pending') return { task: t, status: w.state, pr: w.pr, reason: w.reason }
  }
}

const tasks = Array.isArray(args?.tasks) ? args.tasks : (args?.task ? [args.task] : [])
if (!tasks.length) return 'Aucune tâche. Lance le workflow avec { tasks: ["T001", ...] }.'

const results = []
for (const t of tasks) {
  const r = await deliverTask(t)
  results.push(r)
  if (r.status !== 'done') {
    log(`Chaîne arrêtée après ${t} (${r.status}) : les tâches suivantes partent de main.`)
    break
  }
}
return results
