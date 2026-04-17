// src/pages/AuthPage.jsx
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/UI';
import styles from './AuthPage.module.css';

// ── Shared field component ────────────────────────────────────────────────────
function Field({ label, id, type = 'text', value, onChange, error, placeholder }) {
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <input
        id={id} type={type} value={value} onChange={onChange}
        placeholder={placeholder} autoComplete="off"
        className={`${styles.input} ${error ? styles.inputError : ''}`}
      />
      {error && <span className={styles.fieldError}>{error}</span>}
    </div>
  );
}

// ── Login ─────────────────────────────────────────────────────────────────────
export function LoginPage() {
  const { login }    = useAuth();
  const navigate     = useNavigate();
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.logoMark}>⬡</div>
          <h1 className={styles.title}>PHYSIQ</h1>
          <p className={styles.subtitle}>Adaptive Physics Learning</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <Field label="Email" id="email" type="email"
            value={email} onChange={e => setEmail(e.target.value)}
            placeholder="you@university.edu" />
          <Field label="Password" id="password" type="password"
            value={password} onChange={e => setPassword(e.target.value)}
            placeholder="••••••••" />

          {error && <div className={styles.formError}>{error}</div>}

          <Button type="submit" size="lg" loading={loading}
            className={styles.submitBtn}>
            Initialize Session
          </Button>
        </form>

        <p className={styles.switchText}>
          No account?{' '}
          <Link to="/register" className={styles.switchLink}>Register here</Link>
        </p>
      </div>

      {/* Decorative grid lines */}
      <div className={styles.gridLines} aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className={styles.gridLine} style={{ left: `${i * 14}%` }} />
        ))}
      </div>
    </div>
  );
}

// ── Register ──────────────────────────────────────────────────────────────────
export function RegisterPage() {
  const { register } = useAuth();
  const navigate     = useNavigate();
  const [username,  setUsername]  = useState('');
  const [email,     setEmail]     = useState('');
  const [password,  setPassword]  = useState('');
  const [errors,    setErrors]    = useState({});
  const [loading,   setLoading]   = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    setErrors({});
    setLoading(true);
    try {
      await register(username, email, password);
      navigate('/dashboard');
    } catch (err) {
      if (err.body?.errors) setErrors(err.body.errors);
      else setErrors({ form: err.message || 'Registration failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.logoMark}>⬡</div>
          <h1 className={styles.title}>PHYSIQ</h1>
          <p className={styles.subtitle}>Create Account</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <Field label="Username" id="username"
            value={username} onChange={e => setUsername(e.target.value)}
            error={errors.username} placeholder="your_handle" />
          <Field label="Email" id="email" type="email"
            value={email} onChange={e => setEmail(e.target.value)}
            error={errors.email} placeholder="you@university.edu" />
          <Field label="Password" id="password" type="password"
            value={password} onChange={e => setPassword(e.target.value)}
            error={errors.password} placeholder="min. 8 characters" />

          {errors.form && <div className={styles.formError}>{errors.form}</div>}

          <Button type="submit" size="lg" loading={loading}
            className={styles.submitBtn}>
            Create Account
          </Button>
        </form>

        <p className={styles.switchText}>
          Already registered?{' '}
          <Link to="/login" className={styles.switchLink}>Log in</Link>
        </p>
      </div>

      <div className={styles.gridLines} aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className={styles.gridLine} style={{ left: `${i * 14}%` }} />
        ))}
      </div>
    </div>
  );
}
