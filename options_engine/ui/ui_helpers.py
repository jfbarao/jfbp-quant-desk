import streamlit as st


def section_header(step, title, subtitle):

    st.markdown(f"## {step}. {title}")

    st.caption(subtitle)


def status_pill(label, value="Pending"):

    st.markdown(
        f"""
<div style="
padding:12px;
margin-bottom:8px;
border-radius:10px;
border:1px solid rgba(140,140,140,.25);
background:rgba(255,255,255,.03);
">

<strong>{label}</strong><br>

{value}

</div>
""",
        unsafe_allow_html=True,
    )


def strategy_card(strategy_key, strategy, selected=False):

    with st.container(border=True):

        st.subheader(strategy["name"])

        st.caption(strategy["category"])

        st.write(strategy["description"])

        col1, col2 = st.columns(2)

        col1.metric(
            "Defined Risk",
            "Yes" if strategy["defined_risk"] else "No",
        )

        col2.metric(
            "Requires Shares",
            "Yes" if strategy["requires_shares"] else "No",
        )

        st.markdown(
            f"**Capital Requirement:** {strategy['capital_requirement']}"
        )

        st.markdown(
            f"**Objective:** {strategy['primary_objective']}"
        )

        return st.button(
            "Selected" if selected else "Select Strategy",
            key=f"strategy_{strategy_key}",
            use_container_width=True,
        )