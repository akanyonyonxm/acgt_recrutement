import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Thème corporate ACGT (aligné sur profilis) : bleu nuit + accent jaune.
export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1a237e', // ACGT Night Blue
          secondary: '#0d1b2a', // ACGT Darkest Blue
          accent: '#FDD835', // Jaune du logo
          error: '#D32F2F',
          info: '#0288D1',
          success: '#388E3C',
          warning: '#FBC02D',
          background: '#F5F7FA',
        },
      },
    },
  },
  defaults: {
    VCard: { rounded: 'xl' },
    VTextField: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VSelect: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VTextarea: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VBtn: { rounded: 'lg' },
  },
})
