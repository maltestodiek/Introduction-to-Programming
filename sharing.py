"""User-initiated sharing controls; UniArena never sends a message itself."""

import streamlit as st

from ui_icons import inline_icon


HTML = f"""
<section class="invite-share">
  <div class="invite-heading">
    <span>INVITATION LINK</span><strong class="invite-expiry"></strong>
  </div>
  <div class="invite-url">
    <span class="invite-link"></span>
    <button class="copy" type="button">{inline_icon('copy')}Copy</button>
  </div>
  <div class="invite-channels">
    <button class="native" type="button">{inline_icon('share')}Share</button>
    <a class="whatsapp" target="_blank" rel="noopener">{inline_icon('message')}WhatsApp</a>
    <a class="email">{inline_icon('mail')}Email</a>
  </div>
  <p class="share-status" role="status" aria-live="polite"></p>
</section>
"""

CSS = """
*{box-sizing:border-box}
.invite-share{color:var(--sd-text);font-family:inherit}
.invite-heading{display:flex;align-items:center;justify-content:space-between;gap:.35rem;margin:0 0 12px;color:var(--sd-muted);font-size:.8rem;font-weight:650;letter-spacing:.04em;flex-wrap:wrap}
.invite-expiry{display:flex;align-items:center;gap:5px;color:var(--sd-badge-text);font-size:12px;letter-spacing:0}
.invite-expiry::before{content:"";width:8px;height:8px;flex:none;border-radius:50%;background:var(--sd-success-border)}
.invite-url{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;margin-bottom:12px}
.invite-link{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid var(--sd-border);border-radius:13px;padding:12px;background:var(--sd-surface-muted);color:var(--sd-muted);font-size:13px;line-height:18px}
button,.invite-channels a{display:flex;align-items:center;justify-content:center;gap:.25rem;height:44px;border:1px solid var(--sd-border);border-radius:13px;background:var(--sd-surface);color:var(--sd-text);cursor:pointer;font:inherit;font-size:.875rem;font-weight:600;text-decoration:none;white-space:nowrap}
button.copy{padding:0 .75rem;border-color:var(--sd-action);background:var(--sd-action);color:#fff}
.invite-channels{display:flex;flex-wrap:wrap;gap:6px}
.invite-channels button,.invite-channels a{flex:1 0 auto;height:38px;padding:0 .4rem;font-size:.85rem}
button:hover,.invite-channels a:hover{background:var(--sd-hover)}
button.copy:hover{background:var(--sd-action-hover)}
button:focus-visible,a:focus-visible{outline:3px solid var(--sd-accent);outline-offset:2px}
.share-status:empty{display:none}
.share-status{margin:7px 0 0;color:var(--sd-muted);font-size:11px}
"""

JS = """
export default function ({parentElement, data}) {
  const {url, activeUntil} = data;
  const panel = parentElement.querySelector('.invite-share');
  const link = panel.querySelector('.invite-link');
  const status = panel.querySelector('.share-status');
  link.textContent = link.title = url;
  panel.querySelector('.invite-expiry').textContent = activeUntil;

  const message = encodeURIComponent('Join me on UniArena! Sign in and accept my friend invitation: ' + url);
  panel.querySelector('.whatsapp').href = 'https://wa.me/?text=' + message;
  panel.querySelector('.email').href = 'mailto:?subject=Join%20me%20on%20UniArena&body=' + message;

  panel.querySelector('.copy').onclick = async () => {
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = 'Link copied.';
    } catch {
      status.textContent = 'Select and copy the link.';
    }
  };

  panel.querySelector('.native').onclick = async () => {
    if (!navigator.share) {
      status.textContent = 'Use WhatsApp, Email, or Copy link on this browser.';
      return;
    }
    try {
      await navigator.share({title: 'Join me on UniArena', text: 'Accept my friend invitation on UniArena.', url});
      status.textContent = 'Share menu closed.';
    } catch (error) {
      status.textContent = error.name === 'AbortError' ? 'Sharing cancelled.' : 'Use WhatsApp, Email, or Copy link instead.';
    }
  };
}
"""

_invitation_panel = st.components.v2.component('uniarena_share_invitation', html=HTML, css=CSS, js=JS)


def share_invitation(url, active_until='Invitation link active'):
    """Render a compact, user-controlled invitation sharing panel."""
    _invitation_panel(key='friends_invitation_share', data={'url': url, 'activeUntil': active_until})
