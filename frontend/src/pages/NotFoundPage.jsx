// src/pages/NotFoundPage.jsx
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/UI';
import styles from './NotFoundPage.module.css';

export function NotFoundPage() {
  const { user }   = useAuth();
  const navigate   = useNavigate();
  const destination = user ? '/dashboard' : '/login';
  const label       = user ? 'Back to Dashboard' : 'Go to Login';

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        {/* Glitched 404 display */}
        <div className={styles.code} aria-hidden="true">
          <span className={styles.codeGlitch} data-text="404">404</span>
        </div>

        <h1 className={styles.title}>Signal Lost</h1>
        <p className={styles.body}>
          The coordinates you entered don't exist in this system.
        </p>

        <Button size="lg" onClick={() => navigate(destination)}>
          {label}
        </Button>

        {/* Decorative scan line */}
        <div className={styles.scanWrap} aria-hidden="true">
          <div className={styles.scan} />
        </div>
      </div>
    </div>
  );
}
