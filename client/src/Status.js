import React from "react"
import useSWR from "swr"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { faEllipsisH, faCheckCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons"

import styles from "./App.module.scss"

const status_message = [
    "Loading...",
    "Breqbot is online!",
    "Breqbot is offline."
]

const status_icons = [
    faEllipsisH,
    faCheckCircle,
    faExclamationTriangle
]

const status_colors = [
    "#ccc",
    "#0F0",
    "#F00"
]


function useStatus() {
    const fetcher = (...args) => fetch(...args).then(res => res.json())

    const { data, error } = useSWR("https://bot.api.breq.dev/api/status", fetcher)

    if (error) {
        return {online: 2}
    } else if (data) {
        return {online: 1, ...data}
    } else {
        return {online: 0}
    }
}


function StatusBanner(props) {
    const status = useStatus()

    return (
        <div className={styles.main} style={{backgroundColor: status_colors[status.online]}}>
            <div className={styles.icon}>
                <FontAwesomeIcon icon={status_icons[status.online]} />
            </div>
            <div className={styles.message}>
                <h1>{status_message[status.online]}</h1>
            </div>
        </div>
    )
}

function Statistic(props) {
    return (
        <div className={styles.statistic}>
            <h1>{props.value}</h1>
            <p>{props.name}</p>
        </div>
    )
}


function Statistics(props) {
    const status = useStatus()

    return (
        <div className={styles.statistics}>
            <Statistic name="Servers Joined" value={status.server_count} />
            <Statistic name="Users Served" value={status.user_count} />
            <Statistic name="Commands Run" value={status.commands_run} />
            <Statistic name="Test Server Members" value={status.testing_server_size} />
            <Statistic name="Latest Git Commit" value={status.git_hash ? status.git_hash.substring(0, 7) : "..."} />
        </div>
    )
}

export default function Status(props) {
    return (
        <div>
            <StatusBanner />
            <Statistics />
        </div>
    )
}