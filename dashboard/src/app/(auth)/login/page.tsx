"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../lib/AppContext";
import { supabase } from "../../../lib/supabase";
import { 
  Sparkles, 
  Loader2, 
  AlertTriangle, 
  Mail, 
  Lock, 
  CheckCircle2, 
  ArrowLeft, 
  ShieldCheck, 
  Globe, 
  Eye, 
  EyeOff,
  UserPlus,
  LogIn
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { user, authLoading, isSupabaseConfigured } = useAppContext();

  // Navigation and UI States
  const [lang, setLang] = useState<"es" | "en">("es");
  const [isRegistering, setIsRegistering] = useState<boolean>(false);
  const [otpStep, setOtpStep] = useState<boolean>(false);
  
  // Form Input States
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [verificationCode, setVerificationCode] = useState<string>("");
  
  // Feedback States
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState<boolean>(false);
  
  // OTP Cooldown Timer
  const [cooldown, setCooldown] = useState<number>(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading) {
      if (user) {
        router.push("/analytics");
      }
    }
  }, [authLoading, user, router]);

  // Cooldown countdown timer effect
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown(prev => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Translations
  const t = {
    es: {
      titleLogin: "Iniciar Sesión",
      titleRegister: "Crear Cuenta en GENIA",
      titleOtp: "Verifica tu Correo",
      subtitleLogin: "¿Nuevo en la plataforma?",
      subtitleRegister: "¿Ya tienes una cuenta?",
      subtitleOtp: "Hemos enviado un código a",
      linkRegister: "Regístrate ahora",
      linkLogin: "Inicia sesión",
      labelEmail: "Correo Electrónico",
      labelPassword: "Contraseña",
      labelConfirmPassword: "Confirmar Contraseña",
      labelOtp: "Código de Confirmación (6 dígitos)",
      btnGoogle: "Continuar con Google",
      btnLogin: "Ingresar",
      btnRegister: "Registrarse",
      btnVerify: "Confirmar y Activar",
      btnResend: "Reenviar código",
      btnResendWait: "Reenviar en",
      btnBack: "Volver",
      errSupabase: "Supabase no está configurado. Usando modo de simulación local.",
      errPasswordsMatch: "Las contraseñas no coinciden.",
      errOtpLength: "El código debe ser de 6 dígitos.",
      successOtpSent: "Código enviado. Revisa tu bandeja de entrada.",
      successRegisterMock: "Simulación: Cuenta creada. Por favor ingresa cualquier código de 6 dígitos.",
      successLoginMock: "Simulación: Sesión iniciada con éxito.",
      placeholderEmail: "nombre@correo.com",
      placeholderPassword: "••••••••",
      placeholderConfirmPassword: "••••••••",
      placeholderOtp: "000000",
      dividerOr: "O también",
      checkingSession: "Verificando sesión...",
      redirecting: "Redireccionando..."
    },
    en: {
      titleLogin: "Sign In",
      titleRegister: "Create GENIA Account",
      titleOtp: "Verify Your Email",
      subtitleLogin: "New to the platform?",
      subtitleRegister: "Already have an account?",
      subtitleOtp: "We sent a confirmation code to",
      linkRegister: "Register now",
      linkLogin: "Sign in",
      labelEmail: "Email Address",
      labelPassword: "Password",
      labelConfirmPassword: "Confirm Password",
      labelOtp: "Confirmation Code (6 digits)",
      btnGoogle: "Continue with Google",
      btnLogin: "Sign In",
      btnRegister: "Register",
      btnVerify: "Confirm & Activate",
      btnResend: "Resend code",
      btnResendWait: "Resend in",
      btnBack: "Back",
      errSupabase: "Supabase is not configured. Running in local simulation mode.",
      errPasswordsMatch: "Passwords do not match.",
      errOtpLength: "Code must be 6 digits.",
      successOtpSent: "Code sent. Check your email inbox.",
      successRegisterMock: "Simulation: Account created. Please enter any 6-digit code.",
      successLoginMock: "Simulation: Logged in successfully.",
      placeholderEmail: "name@email.com",
      placeholderPassword: "••••••••",
      placeholderConfirmPassword: "••••••••",
      placeholderOtp: "000000",
      dividerOr: "Or continue with",
      checkingSession: "Checking session...",
      redirecting: "Redirecting..."
    }
  };

  const handleGoogleLogin = async () => {
    setError(null);
    setSubmitLoading(true);

    if (!isSupabaseConfigured || !supabase) {
      // Mock Google Login for development
      setSuccess(t[lang].successLoginMock);
      setTimeout(() => {
        router.push("/analytics");
      }, 1000);
      return;
    }

    try {
      const { error: oAuthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/analytics`
        }
      });
      if (oAuthError) throw oAuthError;
    } catch (err: any) {
      setError(err.message || "Error with Google authentication");
      setSubmitLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    
    if (password !== confirmPassword) {
      setError(t[lang].errPasswordsMatch);
      return;
    }

    setSubmitLoading(true);

    if (!isSupabaseConfigured || !supabase) {
      // Mock Registration Flow
      setTimeout(() => {
        setSuccess(t[lang].successRegisterMock);
        setOtpStep(true);
        setSubmitLoading(false);
      }, 1000);
      return;
    }

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password
      });
      if (signUpError) throw signUpError;
      
      setSuccess(t[lang].successOtpSent);
      setOtpStep(true);
      setCooldown(60); // Start 60s cooldown for resending
    } catch (err: any) {
      setError(err.message || "Registration error");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleVerifyOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (verificationCode.length !== 6) {
      setError(t[lang].errOtpLength);
      return;
    }

    setSubmitLoading(true);

    if (!isSupabaseConfigured || !supabase) {
      // Mock Verification Flow
      setTimeout(() => {
        setSuccess(t[lang].successLoginMock);
        router.push("/analytics");
      }, 1000);
      return;
    }

    try {
      const { data, error: verifyError } = await supabase.auth.verifyOtp({
        email,
        token: verificationCode,
        type: "signup"
      });
      if (verifyError) throw verifyError;
      
      router.push("/analytics");
    } catch (err: any) {
      setError(err.message || "Invalid or expired verification code");
      setSubmitLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitLoading(true);

    if (!isSupabaseConfigured || !supabase) {
      // Mock Login Flow
      setTimeout(() => {
        setSuccess(t[lang].successLoginMock);
        router.push("/analytics");
      }, 1000);
      return;
    }

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password
      });
      if (signInError) throw signInError;
      router.push("/analytics");
    } catch (err: any) {
      setError(err.message || "Failed to log in");
      setSubmitLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0) return;
    setError(null);
    setSuccess(null);

    if (!isSupabaseConfigured || !supabase) {
      setSuccess(t[lang].successOtpSent);
      setCooldown(60);
      return;
    }

    try {
      const { error: resendError } = await supabase.auth.resend({
        type: "signup",
        email: email
      });
      if (resendError) throw resendError;
      
      setSuccess(t[lang].successOtpSent);
      setCooldown(60);
    } catch (err: any) {
      setError(err.message || "Error resending code");
    }
  };

  // Render checking session state
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">{t[lang].checkingSession}</p>
        </div>
      </div>
    );
  }

  // Redirecting loading page (prevent UI flash if session is active)
  if (user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#070b13] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-sm">{t[lang].redirecting}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#070b13] px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      
      {/* Dynamic Background Elements */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-blue-900/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-purple-900/10 blur-[120px] pointer-events-none"></div>

      {/* Language Switcher */}
      <div className="absolute top-6 right-6">
        <button 
          onClick={() => setLang(lang === "es" ? "en" : "es")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900/50 hover:bg-gray-800 border border-gray-800 rounded-xl text-[10px] font-semibold text-white transition cursor-pointer"
        >
          <Globe className="w-3.5 h-3.5 text-blue-400" />
          <span>{lang === "es" ? "English" : "Español"}</span>
        </button>
      </div>

      <div className="w-full max-w-md space-y-6 bg-[#0d1321]/80 backdrop-blur-xl p-8 rounded-3xl border border-gray-850 shadow-2xl relative z-10 transition-all duration-300">
        
        {/* Supabase Missing Warning (Only in Local Dev for Info) */}
        {!isSupabaseConfigured && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{t[lang].errSupabase}</span>
          </div>
        )}

        {/* --- STEP 3: OTP VERIFICATION --- */}
        {otpStep ? (
          <div className="space-y-6">
            <div className="flex flex-col items-center">
              <div className="p-3.5 bg-blue-500/10 text-blue-400 rounded-2xl border border-blue-500/20 mb-4">
                <ShieldCheck className="w-7 h-7" />
              </div>
              <h2 className="text-center text-2xl font-extrabold text-white">
                {t[lang].titleOtp}
              </h2>
              <p className="mt-2 text-center text-xs text-gray-400">
                {t[lang].subtitleOtp} <span className="text-blue-400 font-semibold">{email}</span>
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleVerifyOtpSubmit}>
              {error && (
                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 animate-fadeIn">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-xs flex items-center gap-2 animate-fadeIn">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{success}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-[10px] text-gray-400 font-semibold uppercase">{t[lang].labelOtp}</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                    className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl px-4 py-3 text-center text-lg tracking-[0.5em] font-extrabold text-white focus:outline-none focus:border-blue-500 transition focus:ring-1 focus:ring-blue-500 placeholder-gray-600"
                    placeholder={t[lang].placeholderOtp}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitLoading}
                className="w-full flex justify-center items-center py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/10 hover:shadow-blue-500/20 transition cursor-pointer disabled:opacity-50"
              >
                {submitLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  t[lang].btnVerify
                )}
              </button>

              <div className="flex justify-between items-center text-[10px] mt-4 pt-2 border-t border-gray-850">
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={cooldown > 0}
                  className={`font-semibold cursor-pointer transition ${
                    cooldown > 0 
                      ? "text-gray-500 cursor-not-allowed" 
                      : "text-blue-400 hover:text-blue-300"
                  }`}
                >
                  {cooldown > 0 
                    ? `${t[lang].btnResendWait} ${cooldown}s` 
                    : t[lang].btnResend}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setOtpStep(false);
                    setError(null);
                    setSuccess(null);
                  }}
                  className="flex items-center gap-1 font-semibold text-gray-400 hover:text-white cursor-pointer transition"
                >
                  <ArrowLeft className="w-3 h-3" />
                  <span>{t[lang].btnBack}</span>
                </button>
              </div>
            </form>
          </div>
        ) : (
          /* --- STEPS 1 & 2: LOGIN / REGISTER --- */
          <div className="space-y-6">
            <div className="flex flex-col items-center">
              <div className="p-3 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-2xl shadow-lg mb-4">
                <Sparkles className="w-8 h-8 text-white animate-pulse" />
              </div>
              <h2 className="text-center text-2xl font-extrabold text-white">
                {isRegistering ? t[lang].titleRegister : t[lang].titleLogin}
              </h2>
              <p className="mt-2 text-center text-xs text-gray-400">
                {isRegistering ? t[lang].subtitleRegister : t[lang].subtitleLogin}{" "}
                <button
                  type="button"
                  onClick={() => {
                    setIsRegistering(!isRegistering);
                    setError(null);
                    setSuccess(null);
                  }}
                  className="font-semibold text-blue-400 hover:text-blue-300 focus:outline-none transition cursor-pointer"
                >
                  {isRegistering ? t[lang].linkLogin : t[lang].linkRegister}
                </button>
              </p>
            </div>

            {error && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 animate-fadeIn">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-xs flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{success}</span>
              </div>
            )}

            <form className="space-y-4" onSubmit={isRegistering ? handleRegisterSubmit : handleLoginSubmit}>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 font-semibold uppercase">{t[lang].labelEmail}</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-500" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl pl-11 pr-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500 transition focus:ring-1 focus:ring-blue-500"
                      placeholder={t[lang].placeholderEmail}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 font-semibold uppercase">{t[lang].labelPassword}</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-500" />
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl pl-11 pr-10 py-3 text-xs text-white focus:outline-none focus:border-blue-500 transition focus:ring-1 focus:ring-blue-500"
                      placeholder={t[lang].placeholderPassword}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-3.5 text-gray-500 hover:text-white cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
                    </button>
                  </div>
                </div>

                {isRegistering && (
                  <div className="space-y-1 animate-fadeIn">
                    <label className="text-[10px] text-gray-400 font-semibold uppercase">{t[lang].labelConfirmPassword}</label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-500" />
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full bg-[#161f38] border border-[#2d3a5f] rounded-xl pl-11 pr-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500 transition focus:ring-1 focus:ring-blue-500"
                        placeholder={t[lang].placeholderConfirmPassword}
                      />
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={submitLoading}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/10 hover:shadow-blue-500/20 transition cursor-pointer disabled:opacity-50"
              >
                {submitLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : isRegistering ? (
                  <>
                    <UserPlus className="w-4 h-4" />
                    <span>{t[lang].btnRegister}</span>
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    <span>{t[lang].btnLogin}</span>
                  </>
                )}
              </button>
            </form>

            {/* --- GOOGLE OAUTH DIVIDER & BUTTON --- */}
            <div className="space-y-4">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-800"></div>
                </div>
                <div className="relative flex justify-center text-[10px] uppercase">
                  <span className="bg-[#0d1321] px-2.5 text-gray-500 font-semibold">{t[lang].dividerOr}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={submitLoading}
                className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-[#161f38]/40 hover:bg-[#161f38]/90 text-white text-xs font-bold rounded-xl border border-gray-800 hover:border-gray-700 shadow-md transition duration-200 cursor-pointer disabled:opacity-50"
              >
                <svg className="w-4.5 h-4.5" viewBox="0 0 24 24">
                  <path
                    fill="#EA4335"
                    d="M12 5.04c1.66 0 3.2.57 4.38 1.69l3.27-3.27C17.67 1.54 15.01 1 12 1 7.24 1 3.2 3.73 1.24 7.72l3.82 2.96C6.01 7.33 8.78 5.04 12 5.04z"
                  />
                  <path
                    fill="#4285F4"
                    d="M23.49 12.27c0-.81-.07-1.59-.2-2.36H12v4.51h6.43c-.28 1.44-1.1 2.67-2.33 3.5l3.63 2.81c2.13-1.96 3.76-4.85 3.76-8.46z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.06 10.68c-.25-.72-.38-1.49-.38-2.28s.13-1.56.38-2.28L1.24 7.16C.45 8.76 0 10.33 0 12s.45 3.24 1.24 4.84l3.82-3.16z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c3.24 0 5.97-1.07 7.96-2.92l-3.63-2.81c-1.01.68-2.3 1.09-4.33 1.09-3.22 0-5.99-2.29-6.96-5.64l-3.82 2.96C3.2 20.27 7.24 23 12 23z"
                  />
                </svg>
                <span>{t[lang].btnGoogle}</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
