// Sidebar Component - Reusable navigation sidebar
class SidebarComponent {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.isMobileMenuOpen = false;
        this.isExpanded = false; // Start collapsed by default
    }

    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/index.html') return 'dashboard';
        if (path.includes('notebooks.html')) return 'notebooks';
        if (path.includes('models.html')) return 'models';
        if (path.includes('transformations.html')) return 'transformations';
        if (path.includes('podcasts.html')) return 'podcasts';
        if (path.includes('settings.html')) return 'settings';
        if (path.includes('notebook.html')) return 'notebooks'; // Individual notebook page
        return 'dashboard'; // Default
    }

    render() {
        return `
            <!-- Mobile Menu Overlay -->
            <div class="mobile-menu-overlay" id="mobile-menu-overlay"></div>
            
            <aside class="sidebar" id="sidebar">
                <a href="/index.html" class="sidebar-header-link">
                    <div class="sidebar-header">
                        <img src="./hero.svg" alt="Open Notebook Logo" class="app-logo">
                        <h2>Open Notebook</h2>
                    </div>
                </a>
                <nav class="sidebar-nav">
                    <a href="/index.html" class="nav-item ${this.currentPage === 'dashboard' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-tachometer-alt"></i></span>
                        <span class="nav-text">Dashboard</span>
                    </a>
                    <a href="/notebooks.html" class="nav-item ${this.currentPage === 'notebooks' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-book"></i></span>
                        <span class="nav-text">Notebooks</span>
                    </a>
                    <a href="/models.html" class="nav-item ${this.currentPage === 'models' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-robot"></i></span>
                        <span class="nav-text">Models</span>
                    </a>
                    <a href="/transformations.html" class="nav-item ${this.currentPage === 'transformations' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-exchange-alt"></i></span>
                        <span class="nav-text">Transformations</span>
                    </a>
                    <a href="/podcasts.html" class="nav-item ${this.currentPage === 'podcasts' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-microphone-alt"></i></span>
                        <span class="nav-text">Podcasts</span>
                    </a>
                    <a href="/settings.html" class="nav-item ${this.currentPage === 'settings' ? 'active' : ''}">
                        <span class="nav-icon"><i class="fas fa-cog"></i></span>
                        <span class="nav-text">Settings</span>
                    </a>
                </nav>
                <div class="sidebar-footer">
                    <p class="text-sm opacity-75">AI-powered knowledge management</p>
                </div>
            </aside>
        `;
    }

    init() {
        // Find the sidebar container and inject the sidebar
        const sidebarContainer = document.getElementById('sidebar-container');
        if (sidebarContainer) {
            sidebarContainer.innerHTML = this.render();
        }

        // Set initial state - sidebar starts collapsed
        this.updateSidebarState();

        // Initialize sidebar toggle functionality
        this.initToggle();
    }

    toggleSidebar() {
        this.isExpanded = !this.isExpanded;
        this.updateSidebarState();
    }

    updateSidebarState() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (sidebar && mainContent) {
            if (this.isExpanded) {
                sidebar.classList.add('expanded');
                sidebar.classList.remove('collapsed');
                mainContent.classList.add('sidebar-expanded');
                mainContent.classList.remove('sidebar-collapsed');
            } else {
                sidebar.classList.remove('expanded');
                sidebar.classList.add('collapsed');
                mainContent.classList.remove('sidebar-expanded');
                mainContent.classList.add('sidebar-collapsed');
            }
        }
    }

    toggleMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-menu-overlay');
        const body = document.body;

        if (this.isMobileMenuOpen) {
            // Close mobile menu
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
            body.classList.remove('mobile-menu-open');
            this.isMobileMenuOpen = false;
        } else {
            // Open mobile menu
            sidebar.classList.add('mobile-open');
            overlay.classList.add('active');
            body.classList.add('mobile-menu-open');
            this.isMobileMenuOpen = true;
        }
    }

    closeMobileMenu() {
        if (this.isMobileMenuOpen) {
            this.toggleMobileMenu();
        }
    }

    initToggle() {
        // Use a slight delay to ensure DOM is ready and elements are available
        setTimeout(() => {
            const menuToggle = document.getElementById('menu-toggle');
            const sidebar = document.querySelector('.sidebar');
            const mainContent = document.getElementById('main-content');
            const overlay = document.getElementById('mobile-menu-overlay');

            if (menuToggle) {
                menuToggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Check if we're on mobile
                    if (window.innerWidth <= 768) {
                        this.toggleMobileMenu();
                    } else {
                        // Desktop behavior - toggle sidebar expansion
                        this.toggleSidebar();
                    }
                });
            }

            // Add click functionality to sidebar itself for desktop
            if (sidebar) {
                sidebar.addEventListener('click', (e) => {
                    // Only toggle if we're on desktop and sidebar is collapsed
                    if (window.innerWidth > 768 && !this.isExpanded) {
                        // Don't toggle if clicking on a nav item
                        if (!e.target.closest('.nav-item')) {
                            this.toggleSidebar();
                        }
                    }
                });
            }

            // Close mobile menu when clicking overlay
            if (overlay) {
                overlay.addEventListener('click', () => {
                    this.closeMobileMenu();
                });
            }

            // Close mobile menu when clicking nav items on mobile
            const navItems = document.querySelectorAll('.nav-item');
            navItems.forEach(item => {
                item.addEventListener('click', () => {
                    if (window.innerWidth <= 768) {
                        this.closeMobileMenu();
                    }
                });
            });

            // Handle window resize
            window.addEventListener('resize', () => {
                if (window.innerWidth > 768 && this.isMobileMenuOpen) {
                    this.closeMobileMenu();
                }
            });

            // Close mobile menu on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isMobileMenuOpen) {
                    this.closeMobileMenu();
                }
            });
        }, 100);
    }
}

// Global sidebar instance
let globalSidebar = null;

// Auto-initialize sidebar when script loads
document.addEventListener('DOMContentLoaded', () => {
    globalSidebar = new SidebarComponent();
    globalSidebar.init();
});

// Also try to initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    // DOM is still loading, wait for DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        if (!globalSidebar) {
            globalSidebar = new SidebarComponent();
            globalSidebar.init();
        }
    });
} else {
    // DOM is already loaded
    globalSidebar = new SidebarComponent();
    globalSidebar.init();
}

// Export for manual initialization if needed
window.SidebarComponent = SidebarComponent;
window.globalSidebar = globalSidebar;
