import React from "react"
import useSWR from "swr"
import { Link } from "react-router-dom"

import { Heading } from "@breq/react-theme"

import styles from "./App.module.scss"

function useServerInfo(id) {
    const fetcher = (...args) => fetch(...args).then(res => res.json())

    const guild = useSWR(`https://bot.api.breq.dev/api/guild?id=${id}`, fetcher)
    const richest = useSWR(`https://bot.api.breq.dev/api/richest?id=${id}`, fetcher)
    const shop = useSWR(`https://bot.api.breq.dev/api/shop?id=${id}`, fetcher)

    return {
        guild: guild.data || {},
        richest: richest.data || [],
        shop: shop.data || []
    }
}


function Richest(props) {
    const { richest } = useServerInfo(props.id)

    const rows = richest.map(({balance, id, name}) => (
        <tr>
            <td>
                <Link to={`/${props.id}/${id}`}>{name}</Link>
            </td>
            <td>
                {balance}
            </td>
        </tr>
    ))

    return (
        <div className={styles.table}>
            <h1>Richest Members</h1>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Balance</th>
                </tr>
                {rows}
            </table>
        </div>
    )
}


function Shop(props) {
    const { shop } = useServerInfo(props.id)

    const rows = shop.map(({name, desc, price}) => (
        <tr>
            <td>{name}</td>
            <td>{desc}</td>
            <td>{price}</td>
        </tr>
    ))

    return (
        <div className={styles.table}>
            <h1>Shop</h1>
            <table>
                <tr>
                    <th>Item</th>
                    <th>Description</th>
                    <th>Price</th>
                </tr>
                {rows}
            </table>
        </div>
    )
}

export default function ServerInfo(props) {
    const id = props.match.params[0]
    const { guild } = useServerInfo(id)

    if (guild) {
        return (
            <div>
                <Heading title={guild.name} subtitle={`(${guild.member_count} members)`} />
                <div className={styles.tables}>
                    <Richest id={id} />
                    <Shop id={id} />
                </div>
            </div>
        )
    } else {
        return (
            <div>
                <Heading title="Loading..." subtitle="" />
            </div>
        )
    }
}