import React from "react"
import useSWR from "swr"
import { Link } from "react-router-dom"

import styles from "./App.module.scss"

function useUserInfo(guild_id, user_id) {
    const fetcher = (...args) => fetch(...args).then(res => res.json())

    const profile = useSWR(`https://bot.api.breq.dev/api/profile?id=${user_id}&guild_id=${guild_id}`, fetcher)
    const card = useSWR(`https://bot.api.breq.dev/api/card?id=${user_id}&guild_id=${guild_id}`, fetcher)

    return {
        profile: profile.data || {inventory: [], outfit: []},
        card: card.data || {}
    }
}

function Card(props) {
    const { card } = useUserInfo(props.guild_id, props.user_id)

    const params = new URLSearchParams({format: "html", ...card}).toString()

    return (
        <div className={styles.card}>
            <iframe title="card" src={`https://cards.api.breq.dev/card?${params.toString()}`} />
        </div>
    )
}

function UserInfo(props) {
    const { profile } = useUserInfo(props.guild_id, props.user_id)

    return (
        <div className={styles.userInfo}>
            <h1>{profile.name}</h1>
            <span>is on</span>
            <h3><Link to={`/${props.guild_id}`}>{profile.guild_name}</Link></h3>
            <span>({profile.guild_size} members)</span>
        </div>
    )
}

function UserHeading(props) {
    return (
        <div className={styles.userHeading}>
            <Card {...props} />
            <UserInfo {...props} />
        </div>
    )
}

function Balance(props) {
    const { profile } = useUserInfo(props.guild_id, props.user_id)

    return (
        <div className={styles.balance}>
            <h1>Balance: {profile.balance}</h1>
        </div>
    )
}

function Inventory(props) {
    const { profile } = useUserInfo(props.guild_id, props.user_id)

    const rows = profile.inventory.map(({quantity, name, desc}) => (
        <tr>
            <td>{quantity}</td>
            <td>{name}</td>
            <td>{desc}</td>
        </tr>
    ))

    return (
        <div className={styles.table}>
            <h1>Inventory</h1>
            <table>
                <tr>
                    <th>Qty</th>
                    <th>Item</th>
                    <th>Description</th>
                </tr>
                {rows}
            </table>
        </div>
    )
}

function Outfit(props) {
    const { profile } = useUserInfo(props.guild_id, props.user_id)

    const rows = profile.outfit.map(({name, desc}) => (
        <tr>
            <td>{name}</td>
            <td>{desc}</td>
        </tr>
    ))

    return (
        <div className={styles.table}>
            <h1>Outfit</h1>
            <table>
                <tr>
                    <th>Item</th>
                    <th>Description</th>
                </tr>
                {rows}
            </table>
        </div>
    )
}

export default function ServerInfo(props) {
    const guild_id = props.match.params[0]
    const user_id = props.match.params[1]

    return (
        <div>
            <UserHeading guild_id={guild_id} user_id={user_id} />
            <Balance guild_id={guild_id} user_id={user_id} />
            <div className={styles.tables}>
                <Inventory guild_id={guild_id} user_id={user_id} />
                <Outfit guild_id={guild_id} user_id={user_id} />
            </div>
        </div>
    )
}