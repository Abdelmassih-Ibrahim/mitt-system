export default function Home() {
  return (
    <main className="survival-app">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Vädervett, startsida">
          <span className="brand-mark">V</span>
          <span>VÄDERVETT</span>
        </a>
        <div className="topbar-note">
          <span className="live-dot" />
          <span>DIN PLAN FÖR EN BLÖT DAG</span>
        </div>
        <div className="location-label">
          <span aria-hidden="true">⌖</span> Stockholm
        </div>
      </header>

      <div className="page-content" id="top">
        <section className="weather-hero" aria-labelledby="hero-title">
          <div className="weather-hero__copy">
            <p className="eyebrow eyebrow--light">EXEMPELVÄDER · STOCKHOLM</p>
            <h1 id="hero-title">
              En dag för <span>tak över huvudet.</span>
            </h1>
            <p className="hero-summary">
              Sidoregn, isande vind och en sol som checkar ut tidigt. Vi har en
              plan.
            </p>
            <div className="weather-details">
              <div className="temperature">
                <span className="temperature-value">4°</span>
                <span className="temperature-caption">KÄNNS SOM 0°</span>
              </div>
              <div className="weather-divider" />
              <div className="weather-condition">
                <span className="weather-symbol" aria-hidden="true">
                  🌧️
                </span>
                <span>
                  <strong>Regn på tvären</strong>
                  <small>Vindbyar upp till 12 m/s</small>
                </span>
              </div>
            </div>
          </div>
          <div className="weather-hero__aside">
            <div className="weather-stamp" aria-hidden="true">
              <span>4°</span>
              <span>BLÖTT</span>
            </div>
            <div className="daylight-note">
              <span className="sunset-icon" aria-hidden="true">◒</span>
              <span>
                <small>MÖRKRET KOMMER</small>
                <strong>15:30</strong>
              </span>
            </div>
          </div>
          <span className="hero-coordinate" aria-hidden="true">59°19′N 18°04′E</span>
        </section>

        <section className="plan-section" aria-labelledby="plan-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">MÅNDAGENS ÖVERLEVNADSPLAN</p>
              <h2 id="plan-title">Gör dagen lite lättare.</h2>
            </div>
            <p className="section-aside">Tre små beslut. Mycket torrare dag.</p>
          </div>

          <div className="plan-grid">
            <article className="plan-card outfit-card">
              <div className="card-topline">
                <span className="card-number">01</span>
                <span className="card-label">KLÄDER</span>
              </div>
              <div className="card-icon outfit-icon" aria-hidden="true">↗</div>
              <h3>Lämna paraplyet hemma.</h3>
              <p>
                Vinden vinner den matchen. Ta skaljacka med huva, varm tröja
                och skor som tål pölar.
              </p>
              <div className="card-tip">
                <span className="tip-dot" />
                <span>Reflex på efter 15:30</span>
              </div>
            </article>

            <article className="plan-card activity-card">
              <div className="card-topline">
                <span className="card-number">02</span>
                <span className="card-label">GÖR NÅGOT</span>
              </div>
              <div className="card-icon activity-icon" aria-hidden="true">⌂</div>
              <h3>Byt promenaden mot en utställning.</h3>
              <p>
                Hitta ett museum eller galleri nära dig. Kultur känns ännu
                bättre när jackan får torka i garderoben.
              </p>
              <div className="card-tip">
                <span className="tip-dot" />
                <span>Inomhus · lagom äventyr</span>
              </div>
            </article>

            <article className="plan-card cafe-card">
              <div className="card-topline">
                <span className="card-number">03</span>
                <span className="card-label">TA EN PAUS</span>
              </div>
              <div className="card-icon cafe-icon" aria-hidden="true">☕</div>
              <h3>Gör fikat till huvudnumret.</h3>
              <p>
                Sök skydd på ett kvarterskafé. Beställ något varmt, sitt kvar
                en stund och låt skuren passera.
              </p>
              <div className="card-tip">
                <span className="tip-dot" />
                <span>Nära dig · gärna kanelbulle</span>
              </div>
            </article>
          </div>
        </section>

        <footer className="page-footer">
          <span>VÄDERVETT <span className="footer-mark">/</span> VÄDER MED OMTANKE</span>
          <span>EXEMPELDATA FÖR PROTOTYPEN</span>
        </footer>
      </div>
    </main>
  );
}

