"""Confirm that an incoming chat message reached the recipient's visible thread."""
import streamlit as st


_timestamp = st.components.v2.component(
    "uniarena_chat_receipt",
    html="<span class='timestamp'></span>",
    css=".timestamp {font: inherit; font-size: .875rem; color: var(--st-text-color); opacity: .7;}",
    js="""
export default function({parentElement, data, setStateValue}) {
    const stamp = parentElement.querySelector('.timestamp');
    stamp.textContent = data.label;
    let inView = false;
    let sent = false;
    function acknowledge() {
        if (inView && !document.hidden && !sent) {
            sent = true;
            setStateValue('seen', data.message);
        }
    }
    const observer = new IntersectionObserver(entries => {
        inView = entries[entries.length - 1].intersectionRatio >= 0.9;
        acknowledge();
    }, {threshold: [0, 0.9]});
    observer.observe(stamp);
    document.addEventListener('visibilitychange', acknowledge);
    return () => {
        observer.disconnect();
        document.removeEventListener('visibilitychange', acknowledge);
    };
}
""",
)


def visible_timestamp(thread_id, message_id, label):
    message = str(message_id)
    state = _timestamp(
        data={"message": message, "label": label},
        key=f"chat_receipt_{thread_id}_{message}",
        default={"seen": None},
        on_seen_change=lambda: None,
    )
    return state.seen == message
