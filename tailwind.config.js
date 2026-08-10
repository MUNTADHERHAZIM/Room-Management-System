/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './templates/**/*.html',
        './apps/**/templates/**/*.html',
    ],
    theme: {
        extend: {
            fontFamily: {
                'arabic': ['Cairo', 'Tajawal', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
