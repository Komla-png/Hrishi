/**
 * sidebar.js — Global sidebar behaviour.
 * Handles: collapse/expand toggle, active-link highlighting,
 * Night Mode toggle, and localStorage state persistence.
 *
 * Must be loaded with <script src="/static/sidebar.js"></script>
 * at the bottom of every page's <body>.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var sidebar   = document.getElementById('globalSidebar');
        var toggleBtn = document.getElementById('globalSidebarToggle');
        var nightBtn  = document.getElementById('nightModeToggle');

        if (!sidebar) return;

        /* ----------------------------------------------------------------
           1. Transfer the pre-render "collapsed" state from the <html>
              class (set inline by _sidebar.html) to the sidebar element
              and body, then remove the init class and add sb-ready so CSS
              transitions begin working.
           ---------------------------------------------------------------- */
        var isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

        if (isCollapsed) {
            sidebar.classList.add('collapsed');
            document.body.classList.add('sb-collapsed');
        }

        document.documentElement.classList.remove('sb-collapsed-init');
        document.documentElement.classList.add('sb-ready');

        /* ----------------------------------------------------------------
           2. Active-link highlighting based on current pathname.
              Compares pathname prefix so sub-routes are also highlighted.
           ---------------------------------------------------------------- */
        var currentPath = window.location.pathname;
        var links = sidebar.querySelectorAll('a.sidebar-link');
        var hasServerActive = Array.prototype.some.call(links, function (link) {
            return link.classList.contains('active');
        });

        if (!hasServerActive) {
            links.forEach(function (link) {
                var href = link.getAttribute('href');
                if (!href) return;
                var linkPath = href.split('?')[0];
                // Fallback only: exact root match, prefix for route groups.
                var isActive = (currentPath === linkPath) ||
                               (linkPath.length > 1 && currentPath.startsWith(linkPath));
                if (isActive) {
                    link.classList.add('active');
                }
            });
        }

        /* ----------------------------------------------------------------
           3. Toggle collapse / expand
           ---------------------------------------------------------------- */
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function () {
                var collapsed = sidebar.classList.toggle('collapsed');
                document.body.classList.toggle('sb-collapsed', collapsed);
                localStorage.setItem('sidebarCollapsed', collapsed);

                /* Immediately update all sb-content margins so there is no
                   lag waiting for the CSS transition to finish. */
                document.querySelectorAll('.sb-content').forEach(function (el) {
                    el.style.marginLeft = collapsed ? '60px' : '220px';
                });
            });
        }

        /* ----------------------------------------------------------------
           4. Night Mode toggle
           ---------------------------------------------------------------- */
        if (nightBtn) {
            nightBtn.addEventListener('click', function () {
                var isDark = document.body.classList.toggle('dark-theme');
                try {
                    var prefs = JSON.parse(
                        localStorage.getItem('dashboardPreferences') || '{}'
                    );
                    prefs.theme = isDark ? 'dark' : 'light';
                    localStorage.setItem('dashboardPreferences', JSON.stringify(prefs));
                } catch (e) { /* ignore */ }
            });
        }
    });
}());
