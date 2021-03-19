import React from "react"
import { Page, Heading } from "@breq/react-theme"
import { faGithub, faKeybase } from "@fortawesome/free-brands-svg-icons"

import Status from "./Status"
import Buttons from "./Buttons"
import Info from "./Info"

const links = [
    {
        name: "github",
        href: "https://github.com/breq16/breqbot"
    }
]

const contact = [
    {
        text: "breq",
        icon: faKeybase,
        link: "https://keybase.io/breq"
    },
    {
        text: "breq16",
        icon: faGithub,
        link: "https://github.com/breq16"
    }
]

export default function App(props) {
    return (
        <Page
            brand="breqbot"
            links={links}
            contact={contact}
            author="breq"
            copyright="2021"
            repo="Breq16/breqbot"
        >
            <Heading title="Breqbot" subtitle="A fun Discord bot with games for your server." />
            <Status />
            <Buttons />
            <Info />
            <br />
        </Page>
    )
}
