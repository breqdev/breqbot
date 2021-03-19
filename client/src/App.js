import React from "react"
import { BrowserRouter as Router, Switch, Route } from "react-router-dom"

import { Page, Heading } from "@breq/react-theme"
import { faGithub, faKeybase } from "@fortawesome/free-brands-svg-icons"

import Status from "./Status"
import Buttons from "./Buttons"
import Info from "./Info"
import ServerInfo from "./ServerInfo"
import UserInfo from "./UserInfo"

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
        <Router>
            <Page
                brand="breqbot"
                links={links}
                contact={contact}
                author="breq"
                copyright="2021"
                repo="Breq16/breqbot"
            >
                <div style={{minHeight: "100vh"}}>
                    <Switch>
                        <Route exact path="/">
                            <Heading title="Breqbot" subtitle="A fun Discord bot with games for your server." />
                            <Status />
                            <Buttons />
                            <Info />
                            <br />
                        </Route>
                        <Route path="/*/*" component={UserInfo} />
                        <Route path="/*" component={ServerInfo} />
                    </Switch>
                </div>
            </Page>
        </Router>
    )
}
