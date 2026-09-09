import { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type Locale = 'id' | 'en'

const messages = {
  id: {
    navOverview: 'Ringkasan',
    navTest: 'Mulai tes',
    navResults: 'Hasil Anda',
    navDirections: 'Jelajahi arah',
    navProgress: 'Progress Anda',
    languageLabel: 'Bahasa',
    publicHow: 'Cara kerja',
    publicAssessments: 'Asesmen',
    publicDirections: 'Jelajahi arah',
    publicSchools: 'Untuk sekolah',
    publicMethodology: 'Metodologi',
    signIn: 'Masuk',
    takeTest: 'Mulai tes',
    startTest: 'Mulai tes',
    seeResults: 'Lihat hasil saya',
    resultsReady: 'Hasil Anda sudah siap.',
    seeWhatStandsOut: 'Lihat hal yang menonjol.',
    startWithOneTest: 'Mulai dengan satu tes.',
    seeHowYouThink: 'Lihat cara Anda berpikir.',
    assessmentDescription: 'Asesmen 35 menit dalam tujuh area berpikir, dilanjutkan dengan laporan visual yang jelas.',
    privateProvisional: 'Pribadi dan sementara.',
    notOfficial: 'Ini adalah profil edukasi, bukan skor IQ resmi atau diagnosis.',
    yourResultAppears: 'Hasil Anda akan muncul di sini',
    clearPicture: 'Gambaran yang jelas tentang cara Anda berpikir',
    completeTest: 'Selesaikan tes',
    sevenScores: 'Tujuh skor area, akurasi, dan konteks waktu.',
    firstStep: 'Langkah pertama',
    readyToStart: 'Mulai tes.',
    testFirst: 'Tes dulu. Hasil berikutnya. Arah setelahnya.',
    resultsNext: 'Lihat hasil Anda',
    exploreNext: 'Jelajahi arah',
    testFacts: '56 soal · 35 menit · diacak',
    englishAssessment: 'Asesmen berbahasa Inggris',
    indonesianBankPending: 'Versi soal Bahasa Indonesia sedang disiapkan dan belum dirilis untuk penilaian.',
    adultPilot: 'Saya berusia 18–22 tahun',
    minorPractice: 'Saya berusia 15–17 tahun (mode latihan)',
    chooseAge: 'Pilih kelompok usia sebelum mulai',
    ageRequired: 'Pilih kelompok usia agar kami dapat menjalankan alur yang sesuai.',
    practiceOnly: 'Mode latihan tidak menyimpan jawaban dan tidak menghasilkan skor.',
    practiceComplete: 'Latihan selesai.',
    practiceCompleteBody: 'Tidak ada jawaban atau skor yang disimpan. Saat alur persetujuan wali tersedia, Anda dapat mengikuti asesmen penuh.',
  },
  en: {
    navOverview: 'Overview',
    navTest: 'Take a test',
    navResults: 'Your results',
    navDirections: 'Explore directions',
    navProgress: 'Your progress',
    languageLabel: 'Language',
    publicHow: 'How it works',
    publicAssessments: 'Assessments',
    publicDirections: 'Explore directions',
    publicSchools: 'For schools',
    publicMethodology: 'Methodology',
    signIn: 'Sign in',
    takeTest: 'Take a test',
    startTest: 'Start test',
    seeResults: 'See my results',
    resultsReady: 'Your result is ready.',
    seeWhatStandsOut: 'See what stands out.',
    startWithOneTest: 'Start with one test.',
    seeHowYouThink: 'See how you think.',
    assessmentDescription: 'A 35-minute assessment across seven thinking areas, followed by a clear visual report.',
    privateProvisional: 'Private and provisional.',
    notOfficial: 'This is an educational profile, not an official IQ score or diagnosis.',
    yourResultAppears: 'Your report will appear here',
    clearPicture: 'A clear picture of your thinking',
    completeTest: 'Complete the test',
    sevenScores: 'Seven domain scores, accuracy, and timing context.',
    firstStep: 'The first step',
    readyToStart: 'Start the test.',
    testFirst: 'Test first. Results next. Directions after.',
    resultsNext: 'See your results',
    exploreNext: 'Explore directions',
    testFacts: '56 questions · 35 minutes · randomized',
    englishAssessment: 'English assessment',
    indonesianBankPending: 'The Indonesian item version is being prepared and is not released for scoring yet.',
    adultPilot: 'I am 18–22 years old',
    minorPractice: 'I am 15–17 years old (practice mode)',
    chooseAge: 'Choose an age group before starting',
    ageRequired: 'Choose an age group so we can use the right flow.',
    practiceOnly: 'Practice mode does not save answers or produce a score.',
    practiceComplete: 'Practice complete.',
    practiceCompleteBody: 'No answers or score were saved. When the guardian-consent flow is available, you can take the full assessment.',
  },
} as const

type MessageKey = keyof typeof messages.en

type I18nValue = {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: MessageKey) => string
}

const I18nContext = createContext<I18nValue | null>(null)

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => localStorage.getItem('iaq-locale') === 'en' ? 'en' : 'id')
  useEffect(() => {
    localStorage.setItem('iaq-locale', locale)
    document.documentElement.lang = locale
  }, [locale])
  const value = useMemo<I18nValue>(() => ({ locale, setLocale, t: (key) => messages[locale][key] }), [locale])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const value = useContext(I18nContext)
  if (!value) throw new Error('useI18n must be used inside LocaleProvider')
  return value
}

export function LanguageToggle() {
  const { locale, setLocale, t } = useI18n()
  return <div className="language-toggle" role="group" aria-label={t('languageLabel')}>
    <span>{t('languageLabel')}</span>
    <button type="button" className={locale === 'id' ? 'active' : ''} onClick={() => setLocale('id')} aria-pressed={locale === 'id'}>ID</button>
    <button type="button" className={locale === 'en' ? 'active' : ''} onClick={() => setLocale('en')} aria-pressed={locale === 'en'}>EN</button>
  </div>
}
