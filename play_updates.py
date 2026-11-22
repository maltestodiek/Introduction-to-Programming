"""Read a Play update only after its label is visible in the foreground tab."""
import streamlit as st


_marker = st.components.v2.component(
    'uniarena_play_update',
    html='<span class="update" style="display:inline-block;padding:.18rem .55rem;border-radius:1rem;background:#5142b8;color:white;font:600 .82rem/1.4 system-ui"></span>',
    js="""
export default function({parentElement, data, setStateValue}) {
    const label = parentElement.querySelector('.update');
    label.textContent = data.label;
    let visible = false, timer, sent = false;
    function check() {
        clearTimeout(timer);
        if (visible && !document.hidden && !sent) {
            timer = setTimeout(() => {
                sent = true;
                setStateValue('seen', data.event);
            }, 700);
        }
    }
    const observer = new IntersectionObserver(entries => {
        visible = entries[entries.length-1].intersectionRatio >= 0.9;
        check();
    }, {threshold:[0, 0.9]});
    observer.observe(label);
    document.addEventListener('visibilitychange', check);
    return () => {
        observer.disconnect();
        clearTimeout(timer);
        document.removeEventListener('visibilitychange', check);
    };
}
""",
)


def visible_update(event, label, *, summary=False):
    state = _marker(data={'event':event,'label':label}, key=('summary_' if summary else 'update_')+event,
                    default={'seen':None}, on_seen_change=lambda: None)
    return state.seen == event
