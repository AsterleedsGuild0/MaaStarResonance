// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from "prism-react-renderer";

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/** @type {import('@docusaurus/types').Config} */
const config = {
    title: "星痕共鸣 Maa 小助手",
    tagline: "基于MAAFW的星痕共鸣黑盒测试工具",
    favicon: "img/favicon.ico",

    // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
    future: {
        v4: true, // Improve compatibility with the upcoming Docusaurus v4
    },

    // Set the production url of your site here
    url: "https://maa-star-resonance.vercel.app",
    // Set the /<baseUrl>/ pathname under which your site is served
    // For GitHub pages deployment, it is often '/<projectName>/'
    baseUrl: "/",

    // GitHub pages deployment config.
    // If you aren't using GitHub pages, you don't need these.
    organizationName: "AsterleedsGuild0", // Usually your GitHub org/user name.
    projectName: "MaaStarResonance", // Usually your repo name.

    onBrokenLinks: "throw",

    // Even if you don't use internationalization, you can use this field to set
    // useful metadata like html lang. For example, if your site is Chinese, you
    // may want to replace "en" with "zh-Hans".
    i18n: {
        defaultLocale: "zh-Hans",
        locales: ["zh-Hans"],
    },

    presets: [
        [
            "classic",
            /** @type {import('@docusaurus/preset-classic').Options} */
            ({
                docs: {
                    sidebarPath: "./sidebars.js",
                    // Please change this to your repo.
                    // Remove this to remove the "edit this page" links.
                    editUrl: "https://github.com/AsterleedsGuild0/MaaStarResonance/",
                },
                blog: {
                    showReadingTime: true,
                    feedOptions: {
                        type: ["rss", "atom"],
                        xslt: true,
                    },
                    // Please change this to your repo.
                    // Remove this to remove the "edit this page" links.
                    editUrl: "https://github.com/AsterleedsGuild0/MaaStarResonance/",
                    // Useful options to enforce blogging best practices
                    onInlineTags: "warn",
                    onInlineAuthors: "warn",
                    onUntruncatedBlogPosts: "warn",
                },
                theme: {
                    customCss: "./src/css/custom.css",
                },
            }),
        ],
    ],

    themeConfig:
        /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
        ({
            colorMode: {
                respectPrefersColorScheme: true,
            },
            navbar: {
                title: "星痕共鸣 Maa 小助手",
                logo: {
                    alt: "BPSR",
                    src: "img/favicon.ico",
                },
                items: [
                    {
                        type: "docSidebar",
                        sidebarId: "beginnerSidebar",
                        position: "left",
                        label: "新手指南",
                    },
                    {
                        type: "docSidebar",
                        sidebarId: "featureSidebar",
                        position: "left",
                        label: "功能文档",
                    },
                    {
                        type: "docSidebar",
                        sidebarId: "devSidebar",
                        position: "left",
                        label: "开发文档",
                    },
                    {
                        type: "docSidebar",
                        sidebarId: "aboutSidebar",
                        position: "left",
                        label: "关于我们",
                    },
                ],
            },
            footer: {
                style: "light",
                links: [
                    {
                        title: "Docs",
                        items: [
                            {
                                label: "新手指南",
                                to: "/docs/新手指南/新手指南入口",
                            },
                            {
                                label: "功能文档",
                                to: "/docs/功能文档/功能文档入口",
                            },
                            {
                                label: "开发文档",
                                to: "/docs/开发者文档/开发者文档入口",
                            },
                            {
                                label: "关于我们",
                                to: "/docs/关于/关于我们",
                            },
                        ],
                    },
                ],
                copyright: `Copyright © ${new Date().getFullYear()} MaaStarResonance, Inc. Built with Docusaurus.`,
            },
            prism: {
                theme: prismThemes.github,
                darkTheme: prismThemes.dracula,
            },
        }),
};

export default config;
