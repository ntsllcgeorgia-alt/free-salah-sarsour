"""
Free Salah Sarsour — Campaign Website Builder
==============================================
Deploys a full campaign website to BigCommerce via API.
Dark, powerful design with hero slider, donation links, and case info.

Usage:
    python deploy_campaign.py              # Deploy everything
    python deploy_campaign.py --theme      # Deploy theme CSS only
    python deploy_campaign.py --slides     # Deploy hero slides only
    python deploy_campaign.py --all        # Deploy everything
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

# ═══════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "bc_config.json")

with open(CONFIG_FILE) as f:
    config = json.load(f)

STORE_HASH = config["store_hash"]
ACCESS_TOKEN = config["access_token"]
BASE = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v3"
HEADERS = {
    "X-Auth-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Campaign content
LAUNCHGOOD_URL = "https://www.launchgood.com/v4/campaign/salah_sarsour_justice_fund"
HASHTAG = "#FreeSalahSarsour"

# ═══════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════
def api(method, path, body=None):
    """Make a BigCommerce API call."""
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        print(f"  API Error {e.code}: {err}")
        return None


def create_widget(name, html):
    """Create or update a widget."""
    # Check if widget exists
    data = api("GET", f"/content/widgets?limit=50")
    if data:
        for w in data.get("data", []):
            if w["name"] == name:
                # Update existing
                result = api("PUT", f"/content/widgets/{w['uuid']}", {
                    "widget_configuration": {"htmlCode": html}
                })
                if result:
                    print(f"  Updated widget: {name}")
                    return result["data"]["uuid"]
                return None

    # Create new
    result = api("POST", "/content/widgets", {
        "name": name,
        "widget_template_uuid": get_html_template(),
        "widget_configuration": {"htmlCode": html},
    })
    if result:
        print(f"  Created widget: {name}")
        return result["data"]["uuid"]
    return None


def get_html_template():
    """Get or create the HTML widget template."""
    data = api("GET", "/content/widget-templates?limit=50")
    if data:
        for t in data.get("data", []):
            if t["name"] == "HTML":
                return t["uuid"]

    # Create HTML template
    result = api("POST", "/content/widget-templates", {
        "name": "HTML",
        "schema": [],
        "template": "{{htmlCode}}",
    })
    if result:
        return result["data"]["uuid"]
    return None


def place_widget(widget_uuid, region, template_file, sort_order=0):
    """Place a widget in a region on a page template."""
    result = api("POST", "/content/placements", {
        "widget_uuid": widget_uuid,
        "region": region,
        "template_file": template_file,
        "sort_order": sort_order,
        "status": "active",
    })
    if result:
        print(f"  Placed widget in {region} on {template_file}")
        return result["data"]["uuid"]
    return None


def create_script(name, html):
    """Create a script via the Scripts API."""
    # Delete existing with same name
    data = api("GET", "/content/scripts")
    if data:
        for s in data.get("data", []):
            if s["name"] == name:
                api("DELETE", f"/content/scripts/{s['uuid']}")
                time.sleep(0.5)

    result = api("POST", "/content/scripts", {
        "name": name,
        "description": f"Free Salah Sarsour - {name}",
        "html": html,
        "src": "",
        "auto_uninstall": True,
        "load_method": "default",
        "location": "footer",
        "visibility": "all_pages",
        "kind": "script_tag",
        "consent_category": "essential",
    })
    if result:
        print(f"  Created script: {name}")
        return result["data"]["uuid"]
    return None


# ═══════════════════════════════════════════
# THEME CSS
# ═══════════════════════════════════════════
def get_theme_css():
    return '''<style>
@import url("https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap");

/* === GLOBAL === */
*{box-sizing:border-box}
body{background:#0a0a0a!important;color:#e0e0e0!important;font-family:Inter,Arial,sans-serif;margin:0;padding:0}

/* === HEADER === */
.header{background:#0a0a0a!important;border-bottom:1px solid #1a1a1a!important;padding:12px 0!important}
.header .container{display:flex;align-items:center;justify-content:center;position:relative}
.header-logo{text-align:center!important;margin:0 auto!important}
.header-logo .header-logo-text,.header-logo a{color:#fff!important;font-family:Oswald,sans-serif;font-size:22px!important;font-weight:700;letter-spacing:4px;text-transform:uppercase;text-decoration:none}
.heroCarousel,.section,.productCarousel,.navPages-container{display:none!important}
[data-content-region]{display:block!important}

/* === NAV === */
.navUser{background:transparent!important;position:absolute;right:20px;top:50%;transform:translateY(-50%)}
.navUser-action{color:#888!important;font-size:11px!important}
.navUser-action:hover{color:#00a651!important}

/* === FOOTER === */
.footer{background:#050505!important;color:#666!important;border-top:2px solid #00a651!important}
.footer-info-heading{color:#fff!important;font-family:Oswald,sans-serif;letter-spacing:2px}
.footer a{color:#888!important}
.footer a:hover{color:#00a651!important}

/* === BUTTONS === */
.button--primary{background:#00a651!important;border-color:#00a651!important;color:#fff!important;font-family:Oswald,sans-serif;font-weight:600!important;letter-spacing:2px!important}
.button--primary:hover{background:#008c44!important}

/* === MISC === */
.page,.main.full,#main-content{padding:0!important;margin:0!important}
h1,h2,h3,h4,h5{color:#fff!important;font-family:Oswald,sans-serif}
a{color:#ccc}
a:hover{color:#00a651!important}
</style>'''


# ═══════════════════════════════════════════
# HERO SLIDER
# ═══════════════════════════════════════════
def get_hero_slider():
    return '''<div class="fss-slider" id="fssSlider">

  <!-- SLIDE 1: FREE SALAH SARSOUR -->
  <div class="fss-slide fss-slide-active" style="background:linear-gradient(135deg,rgba(0,0,0,0.85) 0%,rgba(0,40,20,0.8) 50%,rgba(0,0,0,0.9) 100%)">
    <div class="fss-slide-overlay"></div>
    <div class="fss-slide-content">
      <div class="fss-badge">JUSTICE FOR</div>
      <h1 class="fss-title">FREE SALAH<br>SARSOUR</h1>
      <p class="fss-subtitle">Father. Community Leader. Wrongfully Detained.<br>32 Years in America. Zero Criminal Record.</p>
      <div class="fss-buttons">
        <a href="''' + LAUNCHGOOD_URL + '''" target="_blank" class="fss-btn fss-btn-primary">DONATE NOW</a>
        <a href="#story" class="fss-btn fss-btn-outline">READ HIS STORY</a>
      </div>
      <div class="fss-fund-progress">
        <div class="fss-fund-bar"><div class="fss-fund-fill" style="width:37.7%"></div></div>
        <span class="fss-fund-text">$188,747 raised of $500,000 goal &mdash; 1,671 supporters</span>
      </div>
    </div>
  </div>

  <!-- SLIDE 2: WHO IS SALAH SARSOUR -->
  <div class="fss-slide" style="background:linear-gradient(135deg,rgba(10,10,10,0.9) 0%,rgba(20,20,20,0.85) 100%)">
    <div class="fss-slide-content">
      <div class="fss-badge">WHO IS</div>
      <h1 class="fss-title">SALAH<br>SARSOUR</h1>
      <div class="fss-facts">
        <div class="fss-fact"><span class="fss-fact-num">32</span><span class="fss-fact-label">YEARS IN AMERICA</span></div>
        <div class="fss-fact"><span class="fss-fact-num">0</span><span class="fss-fact-label">CRIMINAL CHARGES</span></div>
        <div class="fss-fact"><span class="fss-fact-num">53</span><span class="fss-fact-label">YEARS OLD</span></div>
      </div>
      <p class="fss-subtitle">President of the Islamic Society of Milwaukee &mdash; Wisconsin's largest Islamic organization.<br>A pillar of his community. A father. A man of faith.</p>
      <a href="''' + LAUNCHGOOD_URL + '''" target="_blank" class="fss-btn fss-btn-primary">SUPPORT HIS DEFENSE</a>
    </div>
  </div>

  <!-- SLIDE 3: THE CASE AGAINST HIM -->
  <div class="fss-slide" style="background:linear-gradient(135deg,rgba(80,0,0,0.7) 0%,rgba(10,10,10,0.95) 100%)">
    <div class="fss-slide-content">
      <div class="fss-badge" style="background:rgba(200,0,0,0.3);border-color:#c00">THE CASE</div>
      <h1 class="fss-title">WRONGFULLY<br>DETAINED</h1>
      <div class="fss-case-points">
        <div class="fss-case-point"><span class="fss-point-icon">&#10006;</span> Arrested by 10+ ICE agents &mdash; March 30, 2026</div>
        <div class="fss-case-point"><span class="fss-point-icon">&#10006;</span> Israeli military court conviction at age 15 &mdash; obtained through coercion</div>
        <div class="fss-case-point"><span class="fss-point-icon">&#10006;</span> US government knew his full background when they admitted him in 1993</div>
        <div class="fss-case-point"><span class="fss-point-icon">&#10006;</span> Designated a "foreign policy threat" by Secretary Rubio</div>
        <div class="fss-case-point"><span class="fss-point-icon">&#10006;</span> Case moved to Kansas City &mdash; 95.2% removal rate</div>
      </div>
      <a href="''' + LAUNCHGOOD_URL + '''" target="_blank" class="fss-btn fss-btn-primary">HELP FIGHT THIS INJUSTICE</a>
    </div>
  </div>

  <!-- SLIDE 4: COMMUNITY STANDS WITH HIM -->
  <div class="fss-slide" style="background:linear-gradient(135deg,rgba(0,50,0,0.6) 0%,rgba(10,10,10,0.9) 100%)">
    <div class="fss-slide-content">
      <div class="fss-badge" style="background:rgba(0,166,81,0.2);border-color:#00a651">UNITED</div>
      <h1 class="fss-title">THE COMMUNITY<br>STANDS WITH HIM</h1>
      <p class="fss-subtitle">Hundreds packed the Islamic Society of Milwaukee demanding his release.<br>CAIR, MLFA, faith leaders, elected officials &mdash; all calling for justice.</p>
      <div class="fss-quote">"A pillar taken, a community that will not yield."<br><span class="fss-quote-src">&mdash; Muslim Legal Fund of America</span></div>
      <div class="fss-buttons">
        <a href="''' + LAUNCHGOOD_URL + '''" target="_blank" class="fss-btn fss-btn-primary">JOIN THE MOVEMENT</a>
      </div>
    </div>
  </div>

  <!-- SLIDE 5: DONATE -->
  <div class="fss-slide" style="background:linear-gradient(135deg,rgba(0,80,40,0.7) 0%,rgba(0,0,0,0.9) 100%)">
    <div class="fss-slide-content">
      <div class="fss-badge" style="background:rgba(0,166,81,0.3);border-color:#00a651">TAKE ACTION</div>
      <h1 class="fss-title">SUPPORT<br>THE FIGHT</h1>
      <div class="fss-donate-box">
        <div class="fss-donate-amount">$188,747</div>
        <div class="fss-donate-goal">raised of $500,000 goal</div>
        <div class="fss-fund-bar" style="margin:15px 0"><div class="fss-fund-fill" style="width:37.7%"></div></div>
        <div class="fss-donate-supporters">1,671 supporters &bull; 115 days left</div>
      </div>
      <div class="fss-buttons">
        <a href="''' + LAUNCHGOOD_URL + '''" target="_blank" class="fss-btn fss-btn-donate">DONATE NOW ON LAUNCHGOOD</a>
      </div>
      <p class="fss-hashtag">''' + HASHTAG + '''</p>
    </div>
  </div>

  <!-- SLIDER CONTROLS -->
  <button class="fss-arrow fss-arrow-left" onclick="fssSlide(-1)">&#10094;</button>
  <button class="fss-arrow fss-arrow-right" onclick="fssSlide(1)">&#10095;</button>
  <div class="fss-dots" id="fssDots"></div>
</div>

<style>
/* === SLIDER === */
.fss-slider{position:relative;width:100%;height:100vh;min-height:600px;overflow:hidden;background:#0a0a0a}
.fss-slide{position:absolute;top:0;left:0;width:100%;height:100%;opacity:0;transition:opacity 0.8s ease;display:flex;align-items:center;justify-content:center}
.fss-slide-active{opacity:1;z-index:2}
.fss-slide-overlay{position:absolute;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse at 30% 50%,transparent 0%,rgba(0,0,0,0.4) 100%)}
.fss-slide-content{position:relative;z-index:3;max-width:900px;padding:40px;text-align:center}

/* === BADGE === */
.fss-badge{display:inline-block;font-family:Oswald,sans-serif;font-size:13px;font-weight:600;letter-spacing:4px;color:#00a651;border:1px solid rgba(0,166,81,0.4);background:rgba(0,166,81,0.1);padding:6px 20px;border-radius:30px;margin-bottom:20px;text-transform:uppercase}

/* === TITLE === */
.fss-title{font-family:Oswald,sans-serif;font-size:72px;font-weight:700;color:#fff;line-height:1.05;margin:0 0 20px;text-transform:uppercase;letter-spacing:3px;text-shadow:0 4px 20px rgba(0,0,0,0.5)}

/* === SUBTITLE === */
.fss-subtitle{font-family:Inter,sans-serif;font-size:18px;color:#bbb;line-height:1.6;margin:0 0 30px;font-weight:300}

/* === BUTTONS === */
.fss-buttons{display:flex;gap:15px;justify-content:center;flex-wrap:wrap;margin-bottom:25px}
.fss-btn{font-family:Oswald,sans-serif;font-size:14px;font-weight:600;letter-spacing:3px;text-transform:uppercase;padding:14px 35px;border-radius:4px;text-decoration:none;transition:all 0.3s ease;cursor:pointer;display:inline-block}
.fss-btn-primary{background:#00a651;color:#fff!important;border:2px solid #00a651}
.fss-btn-primary:hover{background:#008c44;border-color:#008c44;transform:translateY(-2px);box-shadow:0 4px 15px rgba(0,166,81,0.3)}
.fss-btn-outline{background:transparent;color:#fff!important;border:2px solid rgba(255,255,255,0.3)}
.fss-btn-outline:hover{border-color:#fff;background:rgba(255,255,255,0.05)}
.fss-btn-donate{background:#00a651;color:#fff!important;border:2px solid #00a651;font-size:16px;padding:16px 45px}
.fss-btn-donate:hover{background:#008c44;transform:translateY(-2px);box-shadow:0 6px 25px rgba(0,166,81,0.4)}

/* === FUND PROGRESS BAR === */
.fss-fund-progress{max-width:400px;margin:0 auto}
.fss-fund-bar{width:100%;height:6px;background:#1a1a1a;border-radius:3px;overflow:hidden}
.fss-fund-fill{height:100%;background:linear-gradient(90deg,#00a651,#00d468);border-radius:3px;transition:width 1s ease}
.fss-fund-text{font-size:12px;color:#888;margin-top:8px;display:block;letter-spacing:0.5px}

/* === FACTS === */
.fss-facts{display:flex;gap:40px;justify-content:center;margin:30px 0}
.fss-fact{text-align:center}
.fss-fact-num{display:block;font-family:Oswald,sans-serif;font-size:56px;font-weight:700;color:#00a651;line-height:1}
.fss-fact-label{display:block;font-size:11px;color:#888;letter-spacing:2px;margin-top:5px;text-transform:uppercase}

/* === CASE POINTS === */
.fss-case-points{text-align:left;max-width:600px;margin:25px auto}
.fss-case-point{font-family:Inter,sans-serif;font-size:16px;color:#ccc;padding:10px 0;border-bottom:1px solid #1a1a1a;display:flex;align-items:center;gap:12px}
.fss-point-icon{color:#c00;font-size:14px;flex-shrink:0}

/* === QUOTE === */
.fss-quote{font-family:Inter,sans-serif;font-size:20px;color:#ddd;font-style:italic;line-height:1.5;margin:25px 0;padding:20px;border-left:3px solid #00a651}
.fss-quote-src{font-size:13px;color:#888;font-style:normal;letter-spacing:1px}

/* === DONATE BOX === */
.fss-donate-box{background:rgba(255,255,255,0.03);border:1px solid #222;border-radius:10px;padding:30px;max-width:400px;margin:25px auto}
.fss-donate-amount{font-family:Oswald,sans-serif;font-size:48px;font-weight:700;color:#00a651}
.fss-donate-goal{font-size:14px;color:#888;margin-top:5px}
.fss-donate-supporters{font-size:13px;color:#666;margin-top:10px}

/* === HASHTAG === */
.fss-hashtag{font-family:Oswald,sans-serif;font-size:20px;color:#00a651;letter-spacing:3px;margin-top:20px}

/* === ARROWS === */
.fss-arrow{position:absolute;top:50%;transform:translateY(-50%);z-index:10;background:rgba(0,0,0,0.4);color:#fff;border:none;font-size:24px;padding:15px 18px;cursor:pointer;transition:background 0.3s;border-radius:4px}
.fss-arrow:hover{background:rgba(0,166,81,0.5)}
.fss-arrow-left{left:20px}
.fss-arrow-right{right:20px}

/* === DOTS === */
.fss-dots{position:absolute;bottom:25px;left:50%;transform:translateX(-50%);z-index:10;display:flex;gap:10px}
.fss-dot{width:12px;height:12px;border-radius:50%;background:rgba(255,255,255,0.2);cursor:pointer;transition:all 0.3s;border:none}
.fss-dot-active{background:#00a651;transform:scale(1.2)}

/* === MOBILE === */
@media(max-width:768px){
  .fss-title{font-size:42px;letter-spacing:1px}
  .fss-subtitle{font-size:15px}
  .fss-facts{gap:20px}
  .fss-fact-num{font-size:36px}
  .fss-slide-content{padding:20px}
  .fss-btn{padding:12px 25px;font-size:12px}
  .fss-arrow{padding:10px 14px;font-size:18px}
  .fss-quote{font-size:16px}
  .fss-donate-amount{font-size:36px}
  .fss-slider{min-height:500px}
}
</style>'''


# ═══════════════════════════════════════════
# SLIDER JAVASCRIPT
# ═══════════════════════════════════════════
def get_slider_script():
    return '''<script>
(function(){
  var current = 0;
  var slides = document.querySelectorAll('.fss-slide');
  var total = slides.length;
  var autoTimer;

  // Create dots
  var dotsContainer = document.getElementById('fssDots');
  if(dotsContainer){
    for(var i=0;i<total;i++){
      var dot = document.createElement('button');
      dot.className = 'fss-dot' + (i===0?' fss-dot-active':'');
      dot.setAttribute('data-index',i);
      dot.onclick = function(){ goTo(parseInt(this.getAttribute('data-index'))); };
      dotsContainer.appendChild(dot);
    }
  }

  function goTo(n){
    slides[current].classList.remove('fss-slide-active');
    var dots = document.querySelectorAll('.fss-dot');
    if(dots[current]) dots[current].classList.remove('fss-dot-active');
    current = (n+total)%total;
    slides[current].classList.add('fss-slide-active');
    if(dots[current]) dots[current].classList.add('fss-dot-active');
    resetAuto();
  }

  window.fssSlide = function(dir){ goTo(current+dir); };

  function resetAuto(){
    clearInterval(autoTimer);
    autoTimer = setInterval(function(){ goTo(current+1); }, 7000);
  }
  resetAuto();

  // Keyboard
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowLeft') goTo(current-1);
    if(e.key==='ArrowRight') goTo(current+1);
  });

  // Touch swipe
  var startX = 0;
  var slider = document.getElementById('fssSlider');
  if(slider){
    slider.addEventListener('touchstart',function(e){ startX=e.touches[0].clientX; });
    slider.addEventListener('touchend',function(e){
      var diff = startX - e.changedTouches[0].clientX;
      if(Math.abs(diff)>50){ goTo(current+(diff>0?1:-1)); }
    });
  }
})();
</script>'''


# ═══════════════════════════════════════════
# DEPLOY
# ═══════════════════════════════════════════
def deploy_theme():
    """Deploy the global dark theme CSS."""
    print("\n  Deploying theme CSS...")
    css = get_theme_css()
    uuid = create_widget("FreeSalah Theme CSS", css)
    if uuid:
        # Place on all page types
        templates = ["pages/home", "pages/category", "pages/product", "pages/page", "pages/search", "pages/cart", "pages/brand"]
        for tmpl in templates:
            place_widget(uuid, "header_bottom--global", tmpl, sort_order=0)
            time.sleep(0.3)
    return uuid


def deploy_slider():
    """Deploy the hero slider."""
    print("\n  Deploying hero slider...")
    slider_html = get_hero_slider()
    uuid = create_widget("FreeSalah Hero Slider", slider_html)
    if uuid:
        place_widget(uuid, "home_below_menu", "pages/home", sort_order=0)
    return uuid


def deploy_slider_script():
    """Deploy the slider JavaScript."""
    print("\n  Deploying slider script...")
    script = get_slider_script()
    return create_script("FreeSalah Slider", script)


def deploy_all():
    """Deploy everything."""
    print("=" * 55)
    print("  FREE SALAH SARSOUR — Campaign Site Deployment")
    print("=" * 55)
    print(f"  Store: {STORE_HASH}")
    print(f"  Donation: {LAUNCHGOOD_URL}")
    print("=" * 55)

    # Check connection
    print("\n  Checking connection...")
    data = api("GET", "/catalog/summary")
    if not data:
        print("  ERROR: Cannot connect to BigCommerce. Check credentials.")
        return

    deploy_theme()
    time.sleep(1)
    deploy_slider()
    time.sleep(1)
    deploy_slider_script()

    print("\n" + "=" * 55)
    print("  DEPLOYMENT COMPLETE")
    print("  Visit your store to see the campaign site!")
    print("=" * 55 + "\n")


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--theme" in args:
        deploy_theme()
    elif "--slides" in args:
        deploy_slider()
        deploy_slider_script()
    else:
        deploy_all()
