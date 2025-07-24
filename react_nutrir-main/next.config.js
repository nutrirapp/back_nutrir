/** @type {import('next').NextConfig} */
const path = require('path');
const withPWA = require('next-pwa')({
    dest: 'public',
    // disable: process.env.NODE_ENV === 'development',
    // register: true,
    // scope: '/app',
    // sw: 'service-worker.js',
    //...
});

module.exports = withPWA({
    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: '170.210.60.215',
                port: '3600',
                pathname: '/media/**',
            },
            {
                protocol: 'http',
                hostname: '127.0.0.1', // opcional para entorno local
                port: '8000',
                pathname: '/media/**',
            },
        ],
    },
});
