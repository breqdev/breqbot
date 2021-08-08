import React from "react"

import styles from "./App.module.scss"

function Card(props) {
    return (
        <div className={styles.card}>
            <h1>{props.title}</h1>
            <p className={styles.subtitle}>{props.subtitle}</p>
            {props.children}
        </div>
    )
}

export default function Info(props) {
    return (
        <div>
            <Card title="Economy" subtitle="Customize your server's economy to your heart's content.">
                With Breqbot, each server has a completely separate economy, with its own shop and items. Unlike other currency bots, members have a separate wallet for each server they join. This keeps communties tight-knit, limits the potential of users to cause harm, and gives server admins the freedom to control their server's economy.

                Admins, or "shopkeepers," can set prices and create items at will. These items and prices are unique to each server. Have a server with your Minecraft buddies? Fill the shop with Minecraft-themed items. Hanging out with LGBTQ+ friends? Let people buy their virtual pride flag! When you can theme your shop around your community, instead of the other way around, the possibilities are endless.
            </Card>
            <Card title="Feeds" subtitle="Share content from a variety of sources.">
                These days, it seems like every bot out there has Reddit commands. But Breqbot can fetch info from an extensive list of sources: everything from Minecraft server MOTDs to XKCD.

                Additionally, Breqbot can watch comics for changes and automatically post them in configurable channels, so you never miss an episode of I Want To Be A Cute Anime Girl.

                Breqbot also uses caching techniques to provide faster Reddit commands than most other Discord bots. By caching top posts from 20+ popular subreddits, Breqbot can send Reddit posts without touching Reddit's API.
            </Card>
            <Card title="Connections" subtitle="Integrate other bots with Breqbot.">
                Bots don't have to be utilitarian. Bots with character can help bring some fun into your Discord server. Breqbot's connection features allow it to send messages to other bots in a fun way.

                Implement Breqbot's "whisper" API to let your bot talk with Breqbot over Discord. Then shoot me a DM to get your bot on Breqbot's whitelist. Bots are more fun when they can talk together, and the possibilities for integrations are vast.
            </Card>
            <Card title="Apps & Games" subtitle="Play together collaboratively, right within Discord.">
                Using some message-reaction trickery, Breqbot can embed games directly within a Discord message. Ever wanted to play 2048 with your friends? Now you can, right within your server.

                The Soundboard app is another feature that sets Breqbot apart. Breqbot can join a voice channel, listen for message reactions, and play sound effects. (Again, these are customizable.)

                Breqbot features a customizable reaction-roles feature as well. Add, remove, and modify role menus - no need to delete and start over just to tweak a few roles.
            </Card>
            <Card title="Portal" subtitle="Connect Discord to the real world like never before.">
                Breqbot's innovative Portal interface allows other modules to connect and provide functionality. But Portal goes beyond the typical "custom commands" feature. With Portal, code is run right on your hardware, providing limitless opportunity for extension.

                Because Portals can be hosted anywhere, they are perfect for connecting Discord apps to real-world devices. No need to worry about setting up a webhook server or port-forwarding - data is sent over a secure WebSocket connection. Set up a Portal from a device like Raspberry Pi, and your server can control your Pi project right from Discord.

                The Portal API allows Portals to set status information - just like Discord bots - and Portal connections will automatically detect failure and reconnect. In other words, Portal handles the hard networking stuff, so you can focus on making the world's most awesome Discord-controlled projects.
            </Card>
            <Card title="Community" subtitle="Join our community to discuss Breqbot and suggest features">
                We have a public Discord server to discuss and test Breqbot. Come join, try out some commands, or request some new features!
            </Card>
        </div>
    )
}