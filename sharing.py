"""User-initiated sharing controls; UniArena never sends a message itself."""
import json
from html import escape
from urllib.parse import quote

import streamlit as st


def share_invitation(url, active_until='Invitation link active'):
    """Render a compact, user-controlled invitation sharing panel."""
    message='Join me on UniArena! Sign in and accept my friend invitation: '+url
    safe_url=escape(url)
    safe_message=quote(message,safe='')
    url_json=json.dumps(url)
    st.components.v1.html(f'''<section class="invite-share">
      <div class="invite-heading"><span>INVITATION LINK</span><strong><i></i>{escape(active_until)}</strong></div>
      <div class="invite-url"><span title="{safe_url}">{safe_url}</span><button class="copy" type="button">▣&nbsp; Copy</button></div>
      <div class="invite-channels">
        <button class="native" type="button">⇧&nbsp; Share</button>
        <a href="https://wa.me/?text={safe_message}" target="_blank" rel="noopener">◉&nbsp; WhatsApp</a>
        <a href="mailto:?subject=Join%20me%20on%20UniArena&body={safe_message}">✉&nbsp; Email</a>
      </div>
      <p class="share-status" role="status" aria-live="polite"></p>
    </section>
    <style>
      *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
      .invite-share{{color:#16223e}}.invite-heading{{display:flex;align-items:center;justify-content:space-between;margin:0 0 12px;color:#747d96;font-size:11px;font-weight:800;letter-spacing:.04em}}
      .invite-heading strong{{display:flex;align-items:center;color:#079281;font-size:12px;letter-spacing:0;text-transform:none}}.invite-heading i{{display:inline-block;width:8px;height:8px;margin-right:5px;border-radius:50%;background:#12a994}}
      .invite-url{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;margin-bottom:12px}}.invite-url span{{display:block;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid #d9dfec;border-radius:13px;padding:12px;color:#68738b;font-size:13px;line-height:18px}}
      button,.invite-channels a{{display:flex;align-items:center;justify-content:center;height:44px;border:1px solid #d9dfec;border-radius:13px;background:#fff;color:#16223e;cursor:pointer;font:700 14px system-ui;text-decoration:none;white-space:nowrap}}button.copy{{padding:0 18px;border-color:#5541e8;background:#5541e8;color:#fff;font-size:14px}}
      .invite-channels{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}.invite-channels button,.invite-channels a{{height:38px;font-size:12px}}button:focus-visible,a:focus-visible{{outline:3px solid #8375ff;outline-offset:2px}}.share-status{{min-height:0;margin:7px 0 0;color:#68738b;font-size:11px}}
    </style>
    <script>
      const url={url_json};const status=document.querySelector('.share-status');
      document.querySelector('.copy').onclick=async()=>{{try{{await navigator.clipboard.writeText(url);status.textContent='Link copied.'}}catch(_error){{status.textContent='Select and copy the link.'}}}};
      document.querySelector('.native').onclick=async()=>{{if(!navigator.share){{status.textContent='Use WhatsApp, Email, or Copy link on this browser.';return}}try{{await navigator.share({{title:'Join me on UniArena',text:'Accept my friend invitation on UniArena.',url}});status.textContent='Share menu closed.'}}catch(error){{status.textContent=error.name==='AbortError'?'Sharing cancelled.':'Use WhatsApp, Email, or Copy link instead.'}}}};
    </script>''',height=136,scrolling=False)
