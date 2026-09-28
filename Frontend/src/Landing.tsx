import { useEffect, useRef, useState } from 'react'
import './Landing.css'

/** Adds .in-view to every [data-reveal] element once it scrolls into the viewport. */
function useReveal(root: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const targets = root.current?.querySelectorAll<HTMLElement>('[data-reveal]') ?? []
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      targets.forEach((el) => el.classList.add('in-view'))
      return
    }
    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view')
          io.unobserve(entry.target)
        }
      }
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.15 })
    targets.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [root])
}

/** Optional looping background. Drop `hero-loop.mp4` into Frontend/public/ and it appears; otherwise nothing renders. */
function HeroVideo() {
  const [state, setState] = useState<'loading' | 'ready' | 'missing'>('loading')
  if (state === 'missing') return null
  return (
    <video
      className={`lhero__video ${state === 'ready' ? 'is-ready' : ''}`}
      src="/hero-loop.mp4"
      autoPlay
      muted
      loop
      playsInline
      preload="metadata"
      aria-hidden="true"
      onCanPlay={() => setState('ready')}
      onError={() => setState('missing')}
    />
  )
}

const navLinks = [
  { label: 'How it works', href: '#how' },
  { label: 'Features', href: '#features' },
  { label: 'For teams', href: '#teams' },
]

const steps = [
  {
    n: '01',
    title: 'A note comes in',
    body: 'The doctor pastes the visit note. CareLoop reads it and turns every action — tests, medication, referrals, follow-ups — into a card with a due date.',
  },
  {
    n: '02',
    title: 'Everyone sees their part',
    body: 'Patients see only their own cards in plain language, with reminders for what is coming up. Doctors see every patient, at-risk flags and what is overdue.',
  },
  {
    n: '03',
    title: 'It closes itself',
    body: '"MRI completed" in a follow-up note closes the MRI card and re-checks anything that depended on it. No one has to tick boxes by hand.',
  },
]

const features = [
  { title: 'Plain-language cards', body: 'Every clinical instruction is rewritten so a worried family member can understand it — without changing its meaning.' },
  { title: 'Dependencies & at-risk flags', body: 'Link cards that depend on each other. If the upstream step stalls, the downstream one is flagged at risk automatically.' },
  { title: 'Reminders that expire', body: 'Cards due within a few days become reminders. Close the card and the reminder is gone.' },
  { title: 'Care-gap recommendations', body: 'When a note mentions a condition, CareLoop checks the plan against what is usually expected and suggests what is missing.' },
  { title: 'Auto-close from evidence', body: 'Follow-up notes that confirm something happened close the matching card as verified — scheduled is not the same as done.' },
  { title: 'Roles that fit the clinic', body: 'Patients, doctors and administrators each get the screen they need, and nothing they do not.' },
]

const stats = [
  { value: '28', label: 'conditions with built-in care checklists' },
  { value: '1', label: 'note is all it takes to start a care plan' },
  { value: '0', label: 'boxes to tick when a step is confirmed done' },
]

const Arrow = () => (
  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 10h12M11 5l5 5-5 5" />
  </svg>
)

export function Landing({ onSignIn }: { onSignIn: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  useReveal(rootRef)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

  return (
    <div className="landing" ref={rootRef}>
      <a className="skip-link" href="#landing-main">Skip to content</a>

      <header className={`lnav ${scrolled ? 'is-scrolled' : ''}`}>
        <a className="lnav__brand" href="#top">
          <span className="brand-mark" aria-hidden="true">CL</span>
          CareLoop
        </a>
        <nav className="lnav__links" aria-label="Primary">
          <ul>
            {navLinks.map((link) => <li key={link.href}><a href={link.href}>{link.label}</a></li>)}
          </ul>
        </nav>
        <div className="lnav__actions">
          <button type="button" className="lbtn lbtn--ghost" onClick={onSignIn}>Sign in</button>
          <button
            type="button"
            className="lnav__burger"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span aria-hidden="true" />
          </button>
        </div>
        {menuOpen && (
          <div className="lnav__sheet">
            <ul>
              {navLinks.map((link) => (
                <li key={link.href}><a href={link.href} onClick={() => setMenuOpen(false)}>{link.label}</a></li>
              ))}
            </ul>
            <button type="button" className="lbtn lbtn--ink" onClick={() => { setMenuOpen(false); onSignIn() }}>Sign in</button>
          </div>
        )}
      </header>

      <main id="landing-main">
        <section className="lhero" id="top">
          <HeroVideo />
          <div className="lhero__glow" aria-hidden="true" />
          <div className="lhero__grid" aria-hidden="true" />

          <div className="lhero__copy">
            <p className="lhero__note rise">
              <span className="dot" aria-hidden="true" />
              Notes into next steps — for patients, doctors and the people who care for them
            </p>
            <h1 className="lhero__title rise">
              The care plan<br />
              that keeps <em>itself</em><br />
              up to date.
            </h1>
            <p className="lhero__sub rise">
              CareLoop turns a doctor&apos;s note into clear cards, reminds patients what is coming,
              flags what is at risk, and closes steps the moment there is evidence they are done.
            </p>
            <div className="lhero__cta rise">
              <button type="button" className="lbtn lbtn--ink lbtn--go" onClick={onSignIn}>
                Open CareLoop
                <span className="lbtn__tile" aria-hidden="true"><Arrow /></span>
              </button>
              <a className="lbtn lbtn--ghost" href="#how">See how it works</a>
            </div>
            <div className="lhero__proof rise">
              <div className="faces" aria-hidden="true">
                <i style={{ '--a': '#0c806d', '--b': '#9ccfc1' } as React.CSSProperties} />
                <i style={{ '--a': '#cf7c31', '--b': '#f3c79b' } as React.CSSProperties} />
                <i style={{ '--a': '#5474a9', '--b': '#a9bde0' } as React.CSSProperties} />
                <i style={{ '--a': '#8b5aa1', '--b': '#cdb3d9' } as React.CSSProperties} />
              </div>
              <span className="lhero__proof-text">
                <strong>One shared list</strong>
                Patient, doctor and administrator views of the same plan
              </span>
            </div>
          </div>

          <aside className="lhero__preview rise" aria-label="Example care card">
            <div className="pcard">
              <div className="pcard__type"><span aria-hidden="true" /> Test <b># 12</b></div>
              <p className="pcard__desc">A brain MRI is a scan that takes detailed pictures of the brain. This helps the care team see what is going on.</p>
              <div className="pcard__meta">
                <span className="pcard__status">Open</span>
                <span className="pcard__due">Due Oct 5</span>
              </div>
            </div>
            <div className="pcard pcard--risk">
              <div className="pcard__type"><span aria-hidden="true" /> Referral <b># 13</b></div>
              <p className="pcard__desc">Schedule a follow-up appointment with Neurology.</p>
              <div className="pcard__meta">
                <span className="pcard__badge">⚠️ At risk</span>
                <span className="pcard__due">Depends on # 12</span>
              </div>
            </div>
            <div className="preminder">
              <span className="preminder__label">Your reminders</span>
              <p>Coming up: Brain MRI (due Oct 5).</p>
            </div>
          </aside>

          <ul className="lstats rise">
            {stats.map((stat) => (
              <li key={stat.label} className="lstat">
                <span className="lstat__value">{stat.value}</span>
                <span className="lstat__label">{stat.label}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="lsection" id="how" aria-labelledby="how-title">
          <p className="eyebrow" data-reveal>How it works</p>
          <h2 id="how-title" className="lsection__title" data-reveal>From note to done, in three moves.</h2>
          <ol className="steps">
            {steps.map((step) => (
              <li key={step.n} className="step" data-reveal>
                <span className="step__n">{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="lsection lsection--tint" id="features" aria-labelledby="features-title">
          <p className="eyebrow" data-reveal>Features</p>
          <h2 id="features-title" className="lsection__title" data-reveal>Small things that stop care from slipping.</h2>
          <ul className="features">
            {features.map((feature) => (
              <li key={feature.title} className="feature" data-reveal>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="lsection" id="teams" aria-labelledby="teams-title">
          <div className="teams">
            <div data-reveal>
              <p className="eyebrow">For teams</p>
              <h2 id="teams-title" className="lsection__title">Built to be changed by the people who use it.</h2>
              <p className="lsection__copy">
                Care checklists, agent prompts and reminder windows live in plain files your team can edit.
                Recommendations are suggestions a clinician approves or dismisses — never silent changes to a plan.
              </p>
              <button type="button" className="lbtn lbtn--ink lbtn--go" onClick={onSignIn}>
                Sign in
                <span className="lbtn__tile" aria-hidden="true"><Arrow /></span>
              </button>
            </div>
            <ul className="roles" data-reveal>
              <li><strong>Patients</strong> see their own cards and reminders, in plain words.</li>
              <li><strong>Doctors</strong> see every patient, at-risk flags, overdue steps and recommendations.</li>
              <li><strong>Administrators</strong> create patients and logins — and nothing clinical.</li>
            </ul>
          </div>
        </section>
      </main>

      <footer className="lfoot" data-reveal>
        <span className="lfoot__mark" aria-hidden="true">CareLoop</span>
        <div className="lfoot__meta">
          <span>CareLoop AI · Notes into next steps</span>
          <button type="button" className="card-toggle" onClick={onSignIn}>Sign in</button>
        </div>
      </footer>
    </div>
  )
}
