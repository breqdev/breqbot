import React from "react"

import styles from "./App.module.scss"

function Button(props) {

    let className = props.primary ? (styles.button + " " + styles.buttonPrimary) : styles.button

    return (
        <a href={props.url} className={className}>
            {props.text}
        </a>
    )
}

export default function Buttons(props) {
    return (
        <div className={styles.buttons}>
            <Button primary text="Invite Breqbot" url="https://bot.api.breq.dev/invite" />
            <Button text="Join Test Server" url="https://bot.api.breq.dev/guild" />
            <Button text="GitHub Repo" url="https://bot.api.breq.dev/github" />
        </div>
    )
}