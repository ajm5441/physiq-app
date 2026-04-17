// src/components/Nav.jsx
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './Nav.module.css';

export function Nav() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className={styles.nav}>
      <div className={styles.navInner}>
        {/* Logo */}
        <NavLink to="/" className={styles.logo}>
          <span className={styles.logoIcon}>⬡</span>
          <span className={styles.logoText}>PHYSIQ</span>
        </NavLink>

        {/* Primary links */}
        {user && (
          <div className={styles.links}>
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.linkActive : ''}`}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/topics"
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.linkActive : ''}`}
            >
              Topics
            </NavLink>
          </div>
        )}

        {/* Right side */}
        <div className={styles.right}>
          {user ? (
            <>
              <span className={styles.username}>{user.username}</span>
              <button onClick={handleLogout} className={styles.logoutBtn}>
                Logout
              </button>
            </>
          ) : (
            <NavLink to="/login" className={styles.link}>Login</NavLink>
          )}
        </div>
      </div>
    </nav>
  );
}
