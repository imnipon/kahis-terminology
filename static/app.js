/**
 * static/app.js
 * Client-side JavaScript for SA-PDT & SNOMED CT Veterinary Extension for KAHIS.
 * Implements Search History (localStorage), Action Icons alignment, and Dynamic Concept Search.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Firebase & Cloud Firestore
    let firestoreDb = null;
    try {
        if (window.firebase) {
            const firebaseConfig = {
                apiKey: "AIzaSyCn5jTgv0Kn2brpnRV8Lvf7XUbHh2_PZhc",
                authDomain: "kahis-terminology.firebaseapp.com",
                projectId: "kahis-terminology",
                storageBucket: "kahis-terminology.firebasestorage.app",
                messagingSenderId: "146556934307",
                appId: "1:146556934307:web:f5f0d06df872ff86d60716"
            };
            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }
            firestoreDb = firebase.firestore();
            console.log('[Firebase] Cloud Firestore initialized successfully.');
        }
    } catch (e) {
        console.warn('[Firebase] Initialization notice:', e);
    }

    // Environment & In-Browser SQLite WASM Engine (sql.js)
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    let localDbInstance = null;
    let sqlModule = null;

    async function getSqlModule() {
        if (!sqlModule && window.initSqlJs) {
            sqlModule = await window.initSqlJs({
                locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/${file}`
            });
        }
        return sqlModule;
    }

    const localDbFileInput = document.getElementById('localDbFileInput');
    const dbStatusPill     = document.getElementById('dbStatusPill');
    const dbStatusLabel    = document.getElementById('dbStatusLabel');
    const btnResetServerDb = document.getElementById('btnResetServerDb');

    // If running in hosted environment (Firebase), indicate Client WASM mode
    if (!isLocalhost && dbStatusLabel && dbStatusPill) {
        dbStatusLabel.textContent = 'Client WASM Mode';
        dbStatusPill.className = 'db-status-pill online';
        dbStatusPill.style.background = '#eff6ff';
        dbStatusPill.style.color = '#1d4ed8';
        dbStatusPill.style.borderColor = '#bfdbfe';
    }

    if (localDbFileInput) {
        localDbFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            dbStatusLabel.textContent = `กำลังโหลด ${file.name}...`;
            dbStatusPill.className = 'db-status-pill loading';

            try {
                const engine = await getSqlModule();
                if (!engine) throw new Error('SQL.js library not loaded');

                let arrayBuffer;
                const isGz = file.name.endsWith('.gz') || file.name.endsWith('.db.gz');

                if (isGz) {
                    dbStatusLabel.textContent = `กำลังคลายการบีบอัด ${file.name}...`;
                    if ('DecompressionStream' in window) {
                        const ds = new DecompressionStream('gzip');
                        const decompressedStream = file.stream().pipeThrough(ds);
                        const decompressedResponse = new Response(decompressedStream);
                        arrayBuffer = await decompressedResponse.arrayBuffer();
                    } else {
                        throw new Error('เบราว์เซอร์ไม่รองรับ DecompressionStream กรุณาใช้ไฟล์ .db แทน');
                    }
                } else {
                    arrayBuffer = await file.arrayBuffer();
                }

                dbStatusLabel.textContent = `กำลังเปิดฐานข้อมูล...`;
                localDbInstance = new engine.Database(new Uint8Array(arrayBuffer));

                const sizeMb = (arrayBuffer.byteLength / (1024 * 1024)).toFixed(1);
                const originalSizeMb = (file.size / (1024 * 1024)).toFixed(1);
                const displayLabel = isGz
                    ? `Local: ${file.name} (${originalSizeMb} MB → ${sizeMb} MB)`
                    : `Local: ${file.name} (${sizeMb} MB)`;

                dbStatusLabel.textContent = displayLabel;
                dbStatusPill.className = 'db-status-pill local-active';
                dbStatusPill.style.background = '#fef3c7';
                dbStatusPill.style.color = '#92400e';
                dbStatusPill.style.borderColor = '#fde68a';

                // Read embedded db_metadata from loaded SQLite DB to update topbar version badges
                try {
                    const metaRes = localDbInstance.exec("SELECT meta_key, meta_value FROM db_metadata");
                    if (metaRes.length > 0 && metaRes[0].values.length > 0) {
                        const metaMap = {};
                        metaRes[0].values.forEach(r => { metaMap[r[0]] = r[1]; });
                        if (badgeSapdt && metaMap.sapdt_badge) badgeSapdt.textContent = metaMap.sapdt_badge;
                        if (badgeVsct  && metaMap.vsct_badge)  badgeVsct.textContent  = metaMap.vsct_badge;
                        if (badgeSct   && metaMap.sct_badge)   badgeSct.textContent   = metaMap.sct_badge;
                        if (badgeKu    && metaMap.ku_badge)    badgeKu.textContent    = metaMap.ku_badge;
                    } else {
                        const mSapdt = file.name.match(/SAPDT(\d{8})/i);
                        const mVsct  = file.name.match(/VSCT(\d{8})/i);
                        const mSct   = file.name.match(/SCT(\d{8})/i);
                        const mKu    = file.name.match(/KU(\d{8})/i);
                        if (badgeSapdt && mSapdt) badgeSapdt.textContent = `SA-PDT ${mSapdt[1]}`;
                        if (badgeVsct  && mVsct)  badgeVsct.textContent  = `VSCT ${mVsct[1]}`;
                        if (badgeSct   && mSct)   badgeSct.textContent   = `SCT ${mSct[1]}`;
                        if (badgeKu    && mKu)    badgeKu.textContent    = `KU ${mKu[1]}`;
                    }
                } catch (metaErr) {
                    console.log('No db_metadata table in loaded DB, checking filename:', metaErr);
                }

                if (btnResetServerDb) {
                    btnResetServerDb.style.display = 'inline-flex';
                    btnResetServerDb.classList.remove('hidden');
                }

                currentPage = 1;
                performSearch();
            } catch (err) {
                console.error('Failed to load SQLite file:', err);
                alert('ไม่สามารถโหลดไฟล์ SQLite: ' + err.message);
                dbStatusLabel.textContent = 'Online Server';
                dbStatusPill.className = 'db-status-pill online';
                dbStatusPill.style.background = '#f0fdf4';
                dbStatusPill.style.color = '#166534';
                dbStatusPill.style.borderColor = '#bbf7d0';
            }
        });
    }

    if (btnResetServerDb) {
        btnResetServerDb.addEventListener('click', () => {
            if (localDbInstance) {
                try { localDbInstance.close(); } catch(e) {}
                localDbInstance = null;
            }
            if (localDbFileInput) localDbFileInput.value = '';
            dbStatusLabel.textContent = 'Online Server';
            dbStatusPill.className = 'db-status-pill online';
            dbStatusPill.style.background = '#f0fdf4';
            dbStatusPill.style.color = '#166534';
            dbStatusPill.style.borderColor = '#bbf7d0';
            btnResetServerDb.style.display = 'none';
            btnResetServerDb.classList.add('hidden');
            initFiltersAndVersions();
            currentPage = 1;
            performSearch();
        });
    }

    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const groupByConcept = document.getElementById('groupByConcept');
    const matchCountBar = document.getElementById('matchCountBar');

    const semanticFilterList = document.getElementById('semanticFilterList');

    const resultsTableBody = document.getElementById('resultsTableBody');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const pageIndicator = document.getElementById('pageIndicator');

    const noConceptState = document.getElementById('noConceptState');
    const conceptLoadedView = document.getElementById('conceptLoadedView');

    // Badges & Topbar
    const badgeSapdt = document.getElementById('badgeSapdt');
    const badgeVsct = document.getElementById('badgeVsct');
    const badgeSct = document.getElementById('badgeSct');
    const badgeKu = document.getElementById('badgeKu');

    // Left Search History & Settings Buttons
    const leftSettingsBtn = document.getElementById('leftSettingsBtn');
    const searchHistoryBtn = document.getElementById('searchHistoryBtn');
    const searchHistoryPopover = document.getElementById('searchHistoryPopover');
    const closeSearchHistoryBtn = document.getElementById('closeSearchHistoryBtn');
    const searchHistoryListItems = document.getElementById('searchHistoryListItems');

    // Right Inspector History & Settings Buttons
    const rightSettingsBtn = document.getElementById('rightSettingsBtn');
    const historyBtn = document.getElementById('historyBtn');
    const historyPopover = document.getElementById('historyPopover');
    const closeHistoryBtn = document.getElementById('closeHistoryBtn');
    const historyListItems = document.getElementById('historyListItems');

    const toastPopup = document.getElementById('toastPopup');

    // Concept details elements
    const conceptTitle = document.getElementById('conceptTitle');
    const conceptSctid = document.getElementById('conceptSctid');
    const conceptSapdtId = document.getElementById('conceptSapdtId');
    const sapdtIdLine = document.getElementById('sapdtIdLine');
    const dbBadgesRow = document.getElementById('dbBadgesRow');
    const conceptFsnFull = document.getElementById('conceptFsnFull');
    const synonymListUl = document.getElementById('synonymListUl');

    const parentsList = document.getElementById('parentsList');
    const childrenList = document.getElementById('childrenList');
    const childrenCount = document.getElementById('childrenCount');
    const attributesStack = document.getElementById('attributesStack');
    const diagramCanvasContainer = document.getElementById('diagramCanvasContainer');
    const downloadDiagramBtn = document.getElementById('downloadDiagramBtn');

    // Resizer Bar Elements
    const leftPane = document.getElementById('leftPane');
    const resizer = document.getElementById('resizer');
    const splitView = document.getElementById('splitView');

    // State Variables
    let currentQuery = '';
    let currentSearchMode = 'prefix';
    let currentStatusMode = 'active';
    let currentDescType = 'all';
    let currentLangRefset = 'all';
    let selectedSemanticTypes = new Set();

    let isGroupByConcept = true;
    let currentPage = 1;
    const pageSize = 50;
    let totalResults = 0;
    let selectedConceptId = null;
    let currentConceptData = null;
    let debounceTimer = null;

    // 1. Draggable Resizer Logic
    let isResizing = false;

    resizer.addEventListener('mousedown', () => {
        isResizing = true;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const containerRect = splitView.getBoundingClientRect();
        let newLeftWidth = e.clientX - containerRect.left;

        const minWidth = 300;
        const maxWidth = containerRect.width - 300;
        if (newLeftWidth < minWidth) newLeftWidth = minWidth;
        if (newLeftWidth > maxWidth) newLeftWidth = maxWidth;

        leftPane.style.width = `${newLeftWidth}px`;
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('dragging');
            document.body.style.cursor = 'default';
        }
    });

    // 2. Custom Green Dropdown Controllers
    function setupCustomDropdown(btnId, panelId, onSelectCallback) {
        const btn = document.getElementById(btnId);
        const panel = document.getElementById(panelId);
        if (!btn || !panel) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.dropdown-panel').forEach(p => {
                if (p !== panel) p.classList.add('hidden');
            });
            panel.classList.toggle('hidden');
        });

        panel.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                panel.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                const val = item.getAttribute('data-value');
                const text = item.textContent;
                
                const prefix = btn.textContent.split(':')[0].replace('▾', '').trim();
                btn.textContent = `${prefix}: ${text} ▾`;
                panel.classList.add('hidden');

                if (onSelectCallback) onSelectCallback(val);
            });
        });
    }

    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-panel').forEach(p => p.classList.add('hidden'));
    });

    setupCustomDropdown('searchModeDropdownBtn', 'searchModePanel', (val) => {
        currentSearchMode = val;
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('statusDropdownBtn', 'statusPanel', (val) => {
        currentStatusMode = val;
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('descTypeDropdownBtn', 'descTypePanel', (val) => {
        currentDescType = val;
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('langRefsetDropdownBtn', 'langRefsetPanel', (val) => {
        currentLangRefset = val;
        currentPage = 1;
        performSearch();
    });

    // 3. Setup Semantic Checkbox Change Listeners (Default All Checked)
    selectedSemanticTypes.clear();
    semanticFilterList.querySelectorAll('input[type="checkbox"]').forEach(chk => {
        if (chk.checked) {
            selectedSemanticTypes.add(chk.value.toLowerCase());
        }
        chk.addEventListener('change', () => {
            const val = chk.value.toLowerCase();
            if (chk.checked) {
                selectedSemanticTypes.add(val);
            } else {
                selectedSemanticTypes.delete(val);
            }
            currentPage = 1;
            performSearch();
        });
    });

    const btnSelectAllTags = document.getElementById('btnSelectAllTags');
    const btnClearAllTags = document.getElementById('btnClearAllTags');

    if (btnSelectAllTags) {
        btnSelectAllTags.addEventListener('click', (e) => {
            e.preventDefault();
            selectedSemanticTypes.clear();
            semanticFilterList.querySelectorAll('input[type="checkbox"]').forEach(chk => {
                chk.checked = true;
                selectedSemanticTypes.add(chk.value.toLowerCase());
            });
            currentPage = 1;
            performSearch();
        });
    }

    if (btnClearAllTags) {
        btnClearAllTags.addEventListener('click', (e) => {
            e.preventDefault();
            selectedSemanticTypes.clear();
            semanticFilterList.querySelectorAll('input[type="checkbox"]').forEach(chk => {
                chk.checked = false;
            });
            currentPage = 1;
            performSearch();
        });
    }

    
    // ===== GLOBAL FLOATING TOOLTIP (Viewport Attached - No Clipping / No Scrollbar) =====
    let floatingTooltip = document.getElementById('floatingInfoTooltip');
    if (!floatingTooltip) {
        floatingTooltip = document.createElement('div');
        floatingTooltip.id = 'floatingInfoTooltip';
        floatingTooltip.className = 'floating-tooltip';
        document.body.appendChild(floatingTooltip);
    }

    document.addEventListener('mouseover', (e) => {
        const btn = e.target.closest('.info-icon-btn');
        if (!btn) return;

        const content = btn.getAttribute('data-tooltip') || btn.querySelector('.info-tooltip-content')?.textContent?.trim();
        if (!content) return;

        floatingTooltip.textContent = content;
        floatingTooltip.classList.add('visible');

        const rect = btn.getBoundingClientRect();
        const tipWidth = floatingTooltip.offsetWidth || 230;
        const tipHeight = floatingTooltip.offsetHeight || 42;

        let left, top;
        // If in left sidebar (rect.left < 260), float to the right side of the icon into the main pane
        if (rect.left < 260) {
            left = rect.right + 10;
            top = rect.top + (rect.height / 2) - (tipHeight / 2);
        } else {
            // Centered above or below
            left = rect.left + (rect.width / 2) - (tipWidth / 2);
            top = rect.top - tipHeight - 8;
        }

        // Boundary checks
        if (top < 10) top = rect.bottom + 8;
        if (left < 10) left = 10;
        if (left + tipWidth > window.innerWidth - 10) {
            left = window.innerWidth - tipWidth - 10;
        }

        floatingTooltip.style.left = `${Math.round(left)}px`;
        floatingTooltip.style.top = `${Math.round(top)}px`;
    });

    document.addEventListener('mouseout', (e) => {
        const btn = e.target.closest('.info-icon-btn');
        if (btn && floatingTooltip) {
            floatingTooltip.classList.remove('visible');
        }
    });

    // 4. Initial Setup
    initFiltersAndVersions();
    performSearch();

    // 5. Generic Toast Notification & Under Construction Popup
    function showToast(msg) {
        if (!toastPopup) return;
        toastPopup.textContent = msg;
        toastPopup.classList.remove('hidden');
        clearTimeout(toastPopup._timer);
        toastPopup._timer = setTimeout(() => {
            toastPopup.classList.add('hidden');
        }, 2500);
    }

    function showUnderConstructionToast() {
        showToast('ฟังก์ชันนี้อยู่ในระหว่างจัดทำ (Under Construction)');
    }

    // ===== FAVORITES SYSTEM (Simulated Clinical User Workflow) =====
    const CURRENT_USER = {
        id: 'vet_user_01',
        name: 'น.สพ. นิพนธ์ วงศ์ประเสริฐ (DVM)',
        clinic: 'คลินิกสัตว์เล็ก'
    };
    const FAV_STORAGE_KEY = `kahis_favorites_${CURRENT_USER.id}`;

    function getFavorites() {
        try {
            return JSON.parse(localStorage.getItem(FAV_STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function saveFavorites(favs) {
        localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(favs));
        updateFavoritesBadge();
    }

    function isConceptFavorite(conceptId) {
        if (!conceptId) return false;
        const favs = getFavorites();
        return favs.some(f => String(f.concept_id) === String(conceptId));
    }

    function toggleFavoriteConcept(conceptData) {
        if (!conceptData) return;
        const cid = String(conceptData.snomed_concept_id || conceptData.concept_id || conceptData.sapdt_concept_id || '');
        if (!cid) return;

        let favs = getFavorites();
        const existingIndex = favs.findIndex(f => String(f.concept_id) === cid);

        const btn = document.getElementById('btnToggleFavorite');
        const starIcon = document.getElementById('starIcon');

        if (existingIndex >= 0) {
            const removedTitle = favs[existingIndex].title;
            favs.splice(existingIndex, 1);
            saveFavorites(favs);
            if (btn) btn.classList.remove('active');
            if (starIcon) starIcon.textContent = '☆';
            showToast(`ลบ "${removedTitle}" ออกจาก Favorites แล้ว`);
        } else {
            const itemTitle = conceptData.display_name || conceptData.snomed_preferred_term || conceptData.snomed_fsn || cid;
            const newItem = {
                concept_id: cid,
                title: itemTitle,
                fsn: conceptData.snomed_fsn || itemTitle,
                semantic_type: conceptData.snomed_semantic_type || '',
                in_sapdt: conceptData.in_sapdt || 'No',
                in_vsct: conceptData.in_vsct || 'No',
                in_sct_inter: conceptData.in_sct_inter || 'No',
                definition_status: conceptData.snomed_definition_status || '',
                added_at: new Date().toISOString()
            };
            favs.unshift(newItem);
            saveFavorites(favs);
            if (btn) btn.classList.add('active');
            if (starIcon) starIcon.textContent = '★';
            showToast(`บันทึก "${itemTitle}" ใน Favorites เรียบร้อย`);
        }

        renderFavoritesPane();
    }

    function updateFavoritesBadge() {
        const favs = getFavorites();
        const countBadge = document.getElementById('favCountBadge');
        if (countBadge) countBadge.textContent = favs.length;
        const countText = document.getElementById('favListCountText');
        if (countText) countText.textContent = `${favs.length} รายการ`;
    }

    function renderFavoritesPane() {
        const favs = getFavorites();
        const container = document.getElementById('favoritesListContainer');
        if (!container) return;

        updateFavoritesBadge();

        if (!favs || favs.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; padding:40px 15px; color:#94a3b8; font-size:13px;">
                    <div style="font-size:32px; margin-bottom:8px; opacity:0.6;">⭐</div>
                    <strong>ยังไม่มีรายการที่บันทึกไว้</strong><br>
                    <span style="font-size:12px; color:#64748b; margin-top:4px; display:inline-block;">กดปุ่มรูปดาว ⭐ ในกล่องสีฟ้า เพื่อบันทึกคำศัพท์ที่ใช้บ่อย</span>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        favs.forEach(item => {
            const row = document.createElement('div');
            row.className = 'fav-card-item';
            
            let badgesHtml = '';
            if (item.in_sapdt === 'Yes') badgesHtml += '<span class="badge-micro badge-sapdt">SA-PDT</span>';
            if (item.in_vsct === 'Yes') badgesHtml += '<span class="badge-micro badge-vsct">VSCT</span>';
            if (item.semantic_type) badgesHtml += `<span class="badge-micro" style="background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd;">${escapeHtml(item.semantic_type)}</span>`;

            row.innerHTML = `
                <div class="fav-card-info" style="flex:1; cursor:pointer;">
                    <div class="fav-card-title" style="font-weight:600; font-size:13px; color:#0f172a;">${escapeHtml(item.title)}</div>
                    <div class="fav-card-sub" style="font-size:11.5px; color:#64748b; margin-top:2px;">ID: ${escapeHtml(item.concept_id)} ${badgesHtml}</div>
                </div>
                <button class="btn-del-fav" title="ลบออกจาก Favorites" style="background:none; border:none; cursor:pointer; color:#94a3b8; font-size:15px; padding:4px 8px; border-radius:4px; transition:all 0.15s;">✕</button>
            `;

            row.querySelector('.fav-card-info').addEventListener('click', () => {
                loadConceptDetails(item.concept_id);
            });

            row.querySelector('.btn-del-fav').addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFavoriteConcept(item);
            });

            container.appendChild(row);
        });
    }

    function updateFavoriteButtonState(conceptId) {
        const btn = document.getElementById('btnToggleFavorite');
        const starIcon = document.getElementById('starIcon');
        if (!btn || !starIcon) return;
        if (isConceptFavorite(conceptId)) {
            btn.classList.add('active');
            starIcon.textContent = '★';
        } else {
            btn.classList.remove('active');
            starIcon.textContent = '☆';
        }
    }

    // Tab Switching: Search vs Favorites
    const tabSearchBtn = document.getElementById('tabSearchBtn');
    const tabFavoritesBtn = document.getElementById('tabFavoritesBtn');
    const searchPaneBody = document.querySelector('.search-pane-body');
    const favoritesPaneContent = document.getElementById('favoritesPaneContent');

    if (tabSearchBtn && tabFavoritesBtn) {
        tabSearchBtn.addEventListener('click', () => {
            tabSearchBtn.classList.add('active');
            tabFavoritesBtn.classList.remove('active');
            if (searchPaneBody) searchPaneBody.classList.remove('hidden');
            if (favoritesPaneContent) favoritesPaneContent.classList.add('hidden');
        });

        tabFavoritesBtn.addEventListener('click', () => {
            tabFavoritesBtn.classList.add('active');
            tabSearchBtn.classList.remove('active');
            if (searchPaneBody) searchPaneBody.classList.add('hidden');
            if (favoritesPaneContent) {
                favoritesPaneContent.classList.remove('hidden');
                renderFavoritesPane();
            }
        });
    }

    // Star Button Toggle Click Listener
    const btnToggleFavorite = document.getElementById('btnToggleFavorite');
    if (btnToggleFavorite) {
        btnToggleFavorite.addEventListener('click', () => {
            if (!currentConceptData) {
                alert('กรุณาเลือกมโนทัศน์ก่อนทำการบันทึก Favorites');
                return;
            }
            toggleFavoriteConcept(currentConceptData);
        });
    }

    // Initialize Favorites UI Badge on Load
    updateFavoritesBadge();

    if (leftSettingsBtn) leftSettingsBtn.addEventListener('click', showUnderConstructionToast);
    if (rightSettingsBtn) rightSettingsBtn.addEventListener('click', showUnderConstructionToast);

    // 6. LEFT PANE: Search History Popover (localStorage)
    searchHistoryBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        searchHistoryPopover.classList.toggle('hidden');
        if (!searchHistoryPopover.classList.contains('hidden')) {
            renderSearchHistoryList();
        }
    });

    closeSearchHistoryBtn.addEventListener('click', () => {
        searchHistoryPopover.classList.add('hidden');
    });

    function saveQueryToSearchHistory(qStr) {
        if (!qStr || qStr.length < 2) return;
        let history = JSON.parse(localStorage.getItem('search_term_history') || '[]');
        history = history.filter(item => item.q !== qStr);
        history.unshift({
            q: qStr,
            time: Date.now()
        });
        if (history.length > 20) history = history.slice(0, 20);
        localStorage.setItem('search_term_history', JSON.stringify(history));
    }

    function renderSearchHistoryList() {
        const history = JSON.parse(localStorage.getItem('search_term_history') || '[]');
        if (!history || history.length === 0) {
            searchHistoryListItems.innerHTML = '<div class="empty-history-text">No search history yet</div>';
            return;
        }

        searchHistoryListItems.innerHTML = '';
        history.forEach(item => {
            const row = document.createElement('div');
            row.className = 'history-item-row';
            row.innerHTML = `
                <span class="history-item-term">${escapeHtml(item.q)}</span>
                <span class="history-item-time">${formatTimeAgo(item.time)}</span>
            `;
            row.addEventListener('click', () => {
                searchHistoryPopover.classList.add('hidden');
                searchInput.value = item.q;
                currentQuery = item.q;
                clearSearchBtn.style.display = 'block';
                currentPage = 1;
                performSearch();
            });
            searchHistoryListItems.appendChild(row);
        });
    }

    // 7. RIGHT PANE: Concept Inspector History Popover (localStorage)
    historyBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        historyPopover.classList.toggle('hidden');
        if (!historyPopover.classList.contains('hidden')) {
            renderHistoryList();
        }
    });

    closeHistoryBtn.addEventListener('click', () => {
        historyPopover.classList.add('hidden');
    });

    document.addEventListener('click', (e) => {
        if (!historyPopover.contains(e.target) && !historyBtn.contains(e.target)) {
            historyPopover.classList.add('hidden');
        }
        if (searchHistoryPopover && !searchHistoryPopover.contains(e.target) && !searchHistoryBtn.contains(e.target)) {
            searchHistoryPopover.classList.add('hidden');
        }
    });

    function saveConceptToHistory(cid, termStr) {
        if (!cid || !termStr) return;
        let history = JSON.parse(localStorage.getItem('concept_history') || '[]');
        history = history.filter(item => item.cid !== cid);
        history.unshift({
            cid: cid,
            term: termStr,
            time: Date.now()
        });
        if (history.length > 20) history = history.slice(0, 20);
        localStorage.setItem('concept_history', JSON.stringify(history));
    }

    function renderHistoryList() {
        const history = JSON.parse(localStorage.getItem('concept_history') || '[]');
        if (!history || history.length === 0) {
            historyListItems.innerHTML = '<div class="empty-history-text">No concept history yet</div>';
            return;
        }

        historyListItems.innerHTML = '';
        history.forEach(item => {
            const row = document.createElement('div');
            row.className = 'history-item-row';
            row.innerHTML = `
                <span class="history-item-term">${escapeHtml(item.term)}</span>
                <span class="history-item-time">${formatTimeAgo(item.time)}</span>
            `;
            row.addEventListener('click', () => {
                historyPopover.classList.add('hidden');
                loadConceptDetails(item.cid);
            });
            historyListItems.appendChild(row);
        });
    }

    function formatTimeAgo(timestamp) {
        const diffSec = Math.floor((Date.now() - timestamp) / 1000);
        if (diffSec < 60) return 'just now';
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return `${diffMin} min ago`;
        const diffHour = Math.floor(diffMin / 60);
        if (diffHour < 24) return `${diffHour} hr ago`;
        return `${Math.floor(diffHour / 24)} d ago`;
    }

    // 8. Search & Inputs Event Listeners
    searchInput.addEventListener('input', (e) => {
        currentQuery = e.target.value.trim();
        clearSearchBtn.style.display = currentQuery ? 'block' : 'none';

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            currentPage = 1;
            performSearch();
        }, 200);
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        currentQuery = '';
        clearSearchBtn.style.display = 'none';
        currentPage = 1;
        performSearch();
    });

    groupByConcept.addEventListener('change', (e) => {
        isGroupByConcept = e.target.checked;
        currentPage = 1;
        performSearch();
    });

    document.getElementById('globalSearch')?.addEventListener('change', () => {
        currentPage = 1;
        performSearch();
    });

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            performSearch();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        if (currentPage * pageSize < totalResults) {
            currentPage++;
            performSearch();
        }
    });

    // Right Sub-Tabs (Summary vs Diagram)
    document.querySelectorAll('.c-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.c-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.sub-tab-panel').forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'tabDiagram') {
                downloadDiagramBtn.classList.remove('hidden');
                if (currentConceptData) {
                    renderStandardDiagramSVG(currentConceptData);
                }
            } else {
                downloadDiagramBtn.classList.add('hidden');
            }
        });
    });

    // 9. API Functions & Dynamic Filters Setup
    async function initFiltersAndVersions() {
        if (!isLocalhost) {
            // In hosted environment, use standard release metadata directly
            if (badgeSapdt) badgeSapdt.textContent = 'SA-PDT 20260930';
            if (badgeVsct)  badgeVsct.textContent  = 'VSCT 20260930';
            if (badgeSct)   badgeSct.textContent   = 'SCT 20261101';
            if (badgeKu)    badgeKu.textContent    = 'KU 20261106';
            return;
        }
        try {
            const res = await fetch('/api/filters');
            const cType = res.headers.get('content-type') || '';
            if (!res.ok || !cType.includes('application/json')) return;
            const data = await res.json();

            if (data.release_versions) {
                if (badgeSapdt) badgeSapdt.textContent = data.release_versions.sapdt || 'SA-PDT 20260930';
                if (badgeVsct)  badgeVsct.textContent  = data.release_versions.vsct  || 'VSCT 20260930';
                if (badgeSct)   badgeSct.textContent   = data.release_versions.sct   || 'SCT 20261101';
                if (badgeKu)    badgeKu.textContent    = data.release_versions.ku    || 'KU 20261106';
            }
        } catch (err) {
            console.warn('Server filters API not available:', err.message);
        }
    }

    function updateSemanticCountBadges(counts = {}) {
        semanticFilterList.querySelectorAll('.filter-item').forEach(label => {
            const chk = label.querySelector('input');
            const badge = label.querySelector('.count-pill');
            if (chk && badge) {
                const tag = chk.value.toLowerCase();
                const cnt = counts[tag] || 0;
                const displayCnt = currentQuery ? cnt : 0;
                badge.textContent = displayCnt;
                if (displayCnt > 0) {
                    badge.classList.add('count-pill-active');
                } else {
                    badge.classList.remove('count-pill-active');
                }
            }
        });
    }

    async function performSearch() {
        const offset = (currentPage - 1) * pageSize;
        const isGlobal = document.getElementById('globalSearch')?.checked || false;
        const params = new URLSearchParams({
            q: currentQuery,
            status: currentStatusMode,
            search_mode: currentSearchMode,
            desc_type: currentDescType,
            lang_refset: currentLangRefset,
            group_by_concept: isGroupByConcept ? 'true' : 'false',
            global_search: isGlobal ? 'true' : 'false',
            limit: pageSize,
            offset: offset
        });

        if (selectedSemanticTypes.size === 0) {
            params.append('empty_semantic', '1');
        } else {
            Array.from(selectedSemanticTypes).forEach(st => params.append('semantic_type', st));
        }

        if (!currentQuery) {
            totalResults = 0;
            matchCountBar.textContent = '0 matches found in 0.00 seconds.';
            resultsTableBody.innerHTML = '';
            updateSemanticCountBadges({});
            updatePagination();
            return;
        }

        // When all semantic filters are unchecked, immediately show 0 matches
        if (selectedSemanticTypes.size === 0) {
            totalResults = 0;
            matchCountBar.textContent = '0 matches found in 0.00 seconds.';
            resultsTableBody.innerHTML = '<tr><td colspan="2" class="empty-msg">No matches found (all semantic filters unchecked)</td></tr>';
            updateSemanticCountBadges({});
            updatePagination();
            return;
        }

        // Hosted Mode Check: If on Firebase Hosting without a loaded local SQLite DB file
        if (!localDbInstance && !isLocalhost) {
            totalResults = 0;
            matchCountBar.textContent = 'กรุณากด "📂 โหลดไฟล์ DB จากเครื่อง" เพื่อค้นหา';
            resultsTableBody.innerHTML = `
                <tr>
                    <td colspan="2" class="empty-msg" style="padding:45px 15px; text-align:center;">
                        <div style="font-size:32px; margin-bottom:8px;">📂</div>
                        <strong style="font-size:14px; color:#1e293b;">โหมดเว็บแอปออนไลน์ (Client-Side WASM)</strong><br>
                        <span style="font-size:12px; color:#64748b; display:inline-block; margin-top:6px; line-height:1.5; max-width:330px;">
                            กรุณากดปุ่ม <strong style="color:#1d4ed8;">"📂 โหลดไฟล์ DB จากเครื่อง"</strong> ที่มุมขวาบน<br>
                            เพื่อเลือกไฟล์ <code>terminology_search.db</code> จากคอมพิวเตอร์ของท่าน
                        </span>
                    </td>
                </tr>`;
            updateSemanticCountBadges({});
            updatePagination();
            return;
        }

        // Save query to search history
        saveQueryToSearchHistory(currentQuery);

        resultsTableBody.innerHTML = '<tr><td colspan="2" class="empty-msg">Searching...</td></tr>';

        if (localDbInstance) {
            try {
                const t0 = performance.now();
                const whereClauses = ["(in_sapdt = 'Yes' OR in_vsct = 'Yes')"];
                const activeCond = "((in_sapdt = 'Yes' AND sapdt_status = 'Active') OR (in_vsct = 'Yes' AND snomed_active = 'Yes'))";
                if (currentStatusMode === 'active') whereClauses.push(activeCond);
                else if (currentStatusMode === 'inactive') whereClauses.push(`NOT ${activeCond}`);

                const sqlParams = [];
                if (/^\d+$/.test(currentQuery)) {
                    whereClauses.push("(snomed_concept_id LIKE ? OR sapdt_concept_id LIKE ? OR sapdt_description_id LIKE ?)");
                    sqlParams.push(`${currentQuery}%`, `${currentQuery}%`, `${currentQuery}%`);
                } else {
                    const words = currentQuery.replace(/["']/g, '').split(/\s+/).filter(Boolean);
                    words.forEach(w => {
                        whereClauses.push(`(display_name LIKE ? OR synonym LIKE ? OR snomed_fsn LIKE ? OR sapdt_fsn LIKE ? OR snomed_preferred_term LIKE ? OR snomed_all_synonyms LIKE ? OR COALESCE(snomed_concept_id, sapdt_concept_id) IN (SELECT concept_id FROM ku_synonym_text WHERE ku_synonym_text LIKE ?))`);
                        const pat = `%${w}%`;
                        sqlParams.push(pat, pat, pat, pat, pat, pat, pat);
                    });
                }

                const baseWhereSql = " WHERE " + whereClauses.join(" AND ");
                const baseParams = [...sqlParams];

                if (selectedSemanticTypes.size > 0) {
                    const stClauses = [];
                    selectedSemanticTypes.forEach(st => {
                        stClauses.push("snomed_semantic_type LIKE ?");
                        sqlParams.push(`%${st}%`);
                    });
                    whereClauses.push("(" + stClauses.join(" OR ") + ")");
                }

                const whereSql = " WHERE " + whereClauses.join(" AND ");
                const groupSql = isGroupByConcept ? " GROUP BY COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id) " : "";
                const cntRes = localDbInstance.exec(`SELECT COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id)) FROM terms ${whereSql}`, sqlParams);
                totalResults = (cntRes.length > 0 && cntRes[0].values.length > 0) ? cntRes[0].values[0][0] : 0;

                const firstWord = currentQuery.split(/\s+/)[0] || '';
                const dataSql = `
                    SELECT id, display_name, in_sapdt, in_vsct, in_sct_inter, sapdt_concept_id,
                           snomed_concept_id, snomed_fsn, snomed_preferred_term, snomed_semantic_type,
                           body_system, match_type, synonym, snomed_definition_status, sapdt_status, snomed_active
                    FROM terms ${whereSql} ${groupSql}
                    ORDER BY CASE WHEN display_name LIKE ? THEN 1 ELSE 2 END, length(display_name) ASC
                    LIMIT ? OFFSET ?
                `;
                const dataRes = localDbInstance.exec(dataSql, [...sqlParams, `${firstWord}%`, pageSize, offset]);
                const rows = [];
                if (dataRes.length > 0) {
                    const cols = dataRes[0].columns;
                    dataRes[0].values.forEach(r => {
                        const obj = {};
                        cols.forEach((c, idx) => obj[c] = r[idx]);
                        rows.push(obj);
                    });
                }

                const semCounts = {};
                const stRes = localDbInstance.exec(`SELECT snomed_semantic_type, COUNT(DISTINCT COALESCE(NULLIF(snomed_concept_id,''), sapdt_concept_id)) FROM terms ${baseWhereSql} GROUP BY snomed_semantic_type`, baseParams);
                if (stRes.length > 0) {
                    stRes[0].values.forEach(r => {
                        if (r[0]) semCounts[String(r[0]).toLowerCase()] = r[1];
                    });
                }

                const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
                matchCountBar.textContent = `${totalResults} matches found in ${elapsed} seconds (Local SQLite).`;
                renderResultsTable(rows);
                updateSemanticCountBadges(semCounts);
                updatePagination();
                return;
            } catch (localErr) {
                console.error('Local SQLite search error:', localErr);
            }
        }

        try {
            const res = await fetch(`/api/search?${params}`);
            const cType = res.headers.get('content-type') || '';
            if (!res.ok || !cType.includes('application/json')) {
                throw new Error('Server returned non-JSON response');
            }
            const data = await res.json();

            totalResults = data.total;
            matchCountBar.textContent = `${totalResults} matches found in ${data.elapsed_sec || '0.05'} seconds.`;

            renderResultsTable(data.results);
            updateSemanticCountBadges(data.semantic_counts || {});
            updatePagination();
        } catch (err) {
            console.error('Search error:', err);
            resultsTableBody.innerHTML = '<tr><td colspan="2" class="empty-msg">Connection error</td></tr>';
        }
    }

    function renderResultsTable(results) {
        if (!results || results.length === 0) {
            resultsTableBody.innerHTML = '<tr><td colspan="2" class="empty-msg">No matches found</td></tr>';
            return;
        }

        resultsTableBody.innerHTML = '';
        results.forEach(item => {
            const cid = item.snomed_concept_id || item.sapdt_concept_id;
            const tr = document.createElement('tr');
            if (selectedConceptId === cid) {
                tr.classList.add('selected');
            }

            const isFullyDefined = item.snomed_definition_status === '900000000000073002';
            const iconHtml = isFullyDefined
                ? '<span class="icon-menu" title="Fully Defined Concept (มโนทัศน์ที่นิยามครบถ้วน)">≡</span>'
                : '<span class="icon-primitive" title="Primitive Concept (มโนทัศน์พื้นฐาน)"></span>';

            const isAct = (item.in_sapdt === 'Yes' && item.sapdt_status === 'Active') ||
                          (item.in_vsct === 'Yes' && item.snomed_active === 'Yes');
            const isSctOnly = (item.in_sapdt === 'No' && item.in_vsct === 'No' && item.in_sct_inter === 'Yes');

            let badgesHtml = '';
            if (item.in_sapdt === 'Yes') {
                badgesHtml += '<span class="badge-micro badge-sapdt">SA-PDT</span>';
            }
            if (item.in_vsct === 'Yes') {
                badgesHtml += '<span class="badge-micro badge-vsct">VSCT</span>';
            }
            if (isSctOnly) {
                badgesHtml += '<span class="badge-micro badge-sct-only">SCT-Inter Only</span>';
            }
            if (!isAct && currentStatusMode === 'all') {
                badgesHtml += '<span class="source-badge-micro micro-inactive">Inactive</span>';
            }

            const badgesRowHtml = badgesHtml ? `<div class="term-badges-row">${badgesHtml}</div>` : '';

            tr.innerHTML = `
                <td class="term-col">
                    <div class="term-title">${iconHtml} ${escapeHtml(item.display_name)}</div>
                    ${badgesRowHtml}
                </td>
                <td class="fsn-col">${escapeHtml(item.snomed_fsn || item.display_name)}</td>
            `;

            tr.addEventListener('click', () => {
                document.querySelectorAll('.results-table tr').forEach(r => r.classList.remove('selected'));
                tr.classList.add('selected');
                selectedConceptId = cid;
                loadConceptDetails(cid);
            });

            resultsTableBody.appendChild(tr);
        });
    }

    function updatePagination() {
        const totalPages = Math.ceil(totalResults / pageSize) || 1;
        pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= totalPages;
    }

    // 10. Load & Render Concept Details Inspector
    async function loadConceptDetails(conceptId) {
        if (!conceptId) return;
        if (localDbInstance) {
            try {
                const qTerm = `SELECT * FROM terms WHERE snomed_concept_id = ? OR sapdt_concept_id = ? LIMIT 1`;
                const res = localDbInstance.exec(qTerm, [conceptId, conceptId]);
                if (res.length > 0 && res[0].values.length > 0) {
                    const cols = res[0].columns;
                    const obj = {};
                    cols.forEach((col, idx) => obj[col] = res[0].values[0][idx]);
                    obj.concept_id = conceptId;

                    const qDesc = `SELECT * FROM ku_synonym_text WHERE concept_id = ?`;
                    const descRes = localDbInstance.exec(qDesc, [conceptId]);
                    const descriptions = [];
                    if (obj.snomed_fsn) descriptions.push({type: 'FSN', text: obj.snomed_fsn, lang: 'en'});
                    if (obj.snomed_preferred_term) descriptions.push({type: 'Preferred', text: obj.snomed_preferred_term, lang: 'en'});
                    if (obj.synonym) {
                        obj.synonym.split('|').forEach(s => {
                            if (s.trim()) descriptions.push({type: 'Synonym', text: s.trim(), lang: 'en'});
                        });
                    }
                    if (descRes.length > 0) {
                        const dCols = descRes[0].columns;
                        descRes[0].values.forEach(dRow => {
                            const dObj = {};
                            dCols.forEach((c, idx) => dObj[c] = dRow[idx]);
                            descriptions.push({type: 'ku', text: dObj.ku_synonym_text || dObj.synonym_text || '', lang: 'ku'});
                        });
                    }
                    obj.descriptions = descriptions;

                    const qRel = `SELECT source_id, destination_id, type_name, destination_term, source_term FROM relationships WHERE source_id = ? OR destination_id = ?`;
                    const relRes = localDbInstance.exec(qRel, [conceptId, conceptId]);
                    const parents = [];
                    const children = [];
                    if (relRes.length > 0) {
                        const rCols = relRes[0].columns;
                        relRes[0].values.forEach(rRow => {
                            const r = {};
                            rCols.forEach((c, idx) => r[c] = rRow[idx]);
                            if (r.source_id === conceptId && (r.type_name === 'Is a' || r.type_name === '116680003')) {
                                parents.push({concept_id: r.destination_id, term: r.destination_term || r.destination_id});
                            } else if (r.destination_id === conceptId && (r.type_name === 'Is a' || r.type_name === '116680003')) {
                                children.push({concept_id: r.source_id, term: r.source_term || r.source_id});
                            }
                        });
                    }
                    obj.parents = parents;
                    obj.children = children;
                    currentConceptData = obj;
                    saveConceptToHistory(conceptId, obj.display_name || obj.snomed_preferred_term || conceptId);
                    renderConceptDetails(obj);
                    loadFirestorePendingSynonyms(conceptId);
                    return;
                }
            } catch (err) {
                console.error('Local concept details error:', err);
            }
        }


        try {
            const res = await fetch(`/api/concept/${conceptId}`);
            const cType = res.headers.get('content-type') || '';
            if (!res.ok || !cType.includes('application/json')) {
                throw new Error('Concept not found or non-JSON response');
            }

            const data = await res.json();
            currentConceptData = data;
            
            const termStr = data.display_name || data.snomed_preferred_term || conceptId;
            saveConceptToHistory(conceptId, termStr);

            renderConceptDetails(data);
            loadFirestorePendingSynonyms(conceptId);
        } catch (err) {
            console.error('Failed to load concept details:', err);
        }
    }

    function renderConceptDetails(data) {
        noConceptState.classList.add('hidden');
        conceptLoadedView.classList.remove('hidden');

        // Blue Card Data
        const titleTerm = data.display_name || data.snomed_preferred_term || data.concept_id;
        const semanticTag = data.snomed_semantic_type ? ` (${data.snomed_semantic_type})` : '';
        
        conceptTitle.textContent = `${titleTerm}${semanticTag}`;
        conceptSctid.textContent = data.snomed_concept_id || data.concept_id;

        // Dynamic Concept Type Icon (Fully Defined ≡ vs Primitive ○ ring)
        const cardTypeIcon = document.getElementById('conceptCardTypeIcon');
        if (cardTypeIcon) {
            const isDef = data.snomed_definition_status === '900000000000073002';
            if (isDef) {
                cardTypeIcon.className = 'card-type-icon';
                cardTypeIcon.textContent = '≡';
                cardTypeIcon.title = 'Fully Defined Concept';
            } else {
                cardTypeIcon.className = 'card-type-icon-primitive';
                cardTypeIcon.textContent = '';
                cardTypeIcon.title = 'Primitive Concept';
            }
        }

        // Update Favorite Star button state
        updateFavoriteButtonState(data.snomed_concept_id || data.concept_id || data.sapdt_concept_id);

        // Clean ID line display (hide redundant SA-PDT ID if identical to SNOMED Concept ID)
        if (data.sapdt_concept_id && data.sapdt_concept_id !== (data.snomed_concept_id || data.concept_id)) {
            sapdtIdLine.style.display = 'block';
            conceptSapdtId.textContent = data.sapdt_concept_id;
        } else {
            sapdtIdLine.style.display = 'none';
        }

        // Database Presence Badges
        dbBadgesRow.innerHTML = '';
        if (data.in_sapdt === 'Yes') {
            dbBadgesRow.innerHTML += '<span class="db-badge-pill db-badge-sapdt">SA-PDT</span>';
        }
        if (data.in_vsct === 'Yes') {
            dbBadgesRow.innerHTML += '<span class="db-badge-pill db-badge-vsct">VSCT</span>';
        }
        if (data.in_sct_inter === 'Yes') {
            dbBadgesRow.innerHTML += '<span class="db-badge-pill db-badge-sct">SCT-Inter</span>';
        }

        conceptFsnFull.textContent = `${data.concept_id} | ${data.snomed_fsn || titleTerm} |`;

        // Synonyms & Descriptions — English White, KU Vibrant Green
        synonymListUl.innerHTML = '';
        const descList = data.descriptions || [];

        if (descList.length > 0) {
            descList.forEach(d => {
                const li = document.createElement('li');
                li.className = 'desc-item';

                // Type badge
                let badgeClass = 'desc-badge-syn';
                if (d.type === 'FSN')       badgeClass = 'desc-badge-fsn';
                if (d.type === 'Preferred') badgeClass = 'desc-badge-pt';
                if (d.type === 'ku')        badgeClass = 'desc-badge-syn desc-badge-ku';

                let badgeText = d.type === 'ku' ? 'Synonym' : d.type;

                if (d.type === 'ku') {
                    li.innerHTML = `<span class="desc-type-badge ${badgeClass}">${escapeHtml(badgeText)}</span> <span class="desc-lang desc-lang-ku">ku</span> <span class="desc-text-ku">${escapeHtml(d.text)}</span>`;
                } else {
                    li.innerHTML = `<span class="desc-type-badge ${badgeClass}">${escapeHtml(badgeText)}</span> <span class="desc-lang">${escapeHtml(d.lang || 'en')}</span> <span class="desc-text">${escapeHtml(d.text)}</span>`;
                }
                synonymListUl.appendChild(li);
            });
        } else {
            if (titleTerm) {
                const li = document.createElement('li');
                li.className = 'desc-item';
                li.innerHTML = `<span class="desc-type-badge desc-badge-pt">Preferred</span> <span class="desc-lang">en</span> <span class="desc-text">${escapeHtml(titleTerm)}</span>`;
                synonymListUl.appendChild(li);
            }
        }

        // Parents Box
        parentsList.innerHTML = '';
        if (data.parents && data.parents.length > 0) {
            data.parents.forEach(p => {
                const div = document.createElement('div');
                div.className = 'parent-item';
                div.innerHTML = `
                    <span>➔ ≡ <strong>${escapeHtml(p.term)}</strong></span>
                    ${renderSourceMicroBadges(p)}
                `;
                div.addEventListener('click', () => loadConceptDetails(p.concept_id));
                parentsList.appendChild(div);
            });
        } else {
            parentsList.innerHTML = '<div class="parent-item">➔ ≡ SNOMED CT Concept (138875005) <span class="source-badge-micro micro-inter">SCT-Inter</span></div>';
        }

        // Attributes Stack
        attributesStack.innerHTML = '';

        if (data.body_system) {
            const card = document.createElement('div');
            card.className = 'attr-card';
            card.innerHTML = `
                <span class="attr-type">Body system</span>
                <span class="attr-arrow">➔</span>
                <span class="attr-target">${escapeHtml(data.body_system)}</span>
            `;
            attributesStack.appendChild(card);
        }

        if (data.attributes && data.attributes.length > 0) {
            data.attributes.forEach(attr => {
                const card = document.createElement('div');
                card.className = 'attr-card';
                card.innerHTML = `
                    <span class="attr-type">${escapeHtml(attr.type_name)}</span>
                    <span class="attr-arrow">➔</span>
                    <span class="attr-target" onclick="loadConceptDetails('${attr.concept_id}')">${escapeHtml(attr.term)}</span>
                `;
                attributesStack.appendChild(card);
            });
        } else if (!data.body_system) {
            attributesStack.innerHTML = '<div class="attr-card"><span class="attr-type">No extra attributes</span></div>';
        }

        // Children Box — CONFLICT-03 FIX: show total count, indicate truncation
        const totalChildCount = data.children_total_count || (data.children ? data.children.length : 0);
        const shownCount = data.children ? data.children.length : 0;
        const isTruncated = totalChildCount > shownCount;

        // Update header count badge
        childrenCount.textContent = totalChildCount;

        childrenList.innerHTML = '';
        if (data.children && data.children.length > 0) {
            data.children.forEach(c => {
                const div = document.createElement('div');
                div.className = 'parent-item';
                div.innerHTML = `
                    <span>&#10132; &#8801; ${escapeHtml(c.term)}</span>
                    ${renderSourceMicroBadges(c)}
                `;
                div.addEventListener('click', () => loadConceptDetails(c.concept_id));
                childrenList.appendChild(div);
            });

            // Show truncation notice if total > 50
            if (isTruncated) {
                const notice = document.createElement('div');
                notice.className = 'children-truncated-notice';
                notice.textContent = `Showing first ${shownCount} of ${totalChildCount} children. Open a SNOMED CT Browser for full hierarchy.`;
                childrenList.appendChild(notice);
            }
        } else {
            childrenList.innerHTML = '<div class="no-children-text">No children</div>';
        }

        // Render Diagram if Diagram tab is active
        const diagramTab = document.querySelector('.c-tab[data-tab="tabDiagram"]');
        if (diagramTab && diagramTab.classList.contains('active')) {
            renderStandardDiagramSVG(data);
        }
    }

    function renderSourceMicroBadges(item) {
        let badgesHtml = '';
        if (item.is_active === false) {
            badgesHtml += '<span class="source-badge-micro micro-inactive">Inactive</span> ';
        }
        if (item.in_sapdt === 'Yes') badgesHtml += '<span class="source-badge-micro micro-sapdt">SA-PDT</span> ';
        if (item.in_vsct === 'Yes') badgesHtml += '<span class="source-badge-micro micro-vsct">VSCT</span> ';
        if (item.in_sct_inter === 'Yes') badgesHtml += '<span class="source-badge-micro micro-inter">SCT-Inter</span>';
        return `<span style="margin-left:auto">${badgesHtml}</span>`;
    }

    // Official SNOMED CT Diagram Standard SVG Generator with Auto-Width
    function renderStandardDiagramSVG(data) {
        const titleTerm = data.display_name || data.concept_id;
        const sctid = data.concept_id;

        function calcBoxWidth(textStr, minW = 220) {
            const charCount = textStr ? textStr.length : 10;
            return Math.max(minW, Math.min(450, charCount * 8 + 30));
        }

        const mainCardWidth = calcBoxWidth(titleTerm, 240);

        let nodesHtml = '';
        let currentY = 40;
        let maxCanvasWidth = 850;

        // 1. Parent Concepts
        if (data.parents && data.parents.length > 0) {
            data.parents.forEach((p) => {
                const pBoxW = calcBoxWidth(p.term, 240);
                if (360 + pBoxW > maxCanvasWidth) maxCanvasWidth = 360 + pBoxW + 40;

                nodesHtml += `
                    <path d="M 296 60 L 325 60 L 325 ${currentY + 20} L 360 ${currentY + 20}" stroke="#000" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>
                    <g transform="translate(360, ${currentY})">
                        <rect width="${pBoxW}" height="42" rx="3" fill="#a4c2f4" stroke="#337ab7" stroke-width="1.5"/>
                        <text x="8" y="16" font-size="10" font-weight="bold" fill="#000">${p.concept_id}</text>
                        <text x="8" y="31" font-size="11" font-weight="600" fill="#000">${escapeHtml(p.term)}</text>
                    </g>
                `;
                currentY += 55;
            });
        } else {
            nodesHtml += `
                <path d="M 296 60 L 360 60" stroke="#000" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>
                <g transform="translate(360, 40)">
                    <rect width="250" height="42" rx="3" fill="#a4c2f4" stroke="#337ab7" stroke-width="1.5"/>
                    <text x="8" y="16" font-size="10" font-weight="bold" fill="#000">138875005</text>
                    <text x="8" y="31" font-size="11" font-weight="600" fill="#000">SNOMED CT Concept (concept)</text>
                </g>
            `;
            currentY += 55;
        }

        // 2. Attributes
        if (data.attributes && data.attributes.length > 0) {
            data.attributes.forEach((attr) => {
                const attrOvalW = calcBoxWidth(attr.type_name, 160);
                const valBoxW = calcBoxWidth(attr.term, 240);
                const valBoxX = 370 + attrOvalW + 20;

                if (valBoxX + valBoxW > maxCanvasWidth) maxCanvasWidth = valBoxX + valBoxW + 40;

                nodesHtml += `
                    <path d="M 296 60 L 325 60 L 325 ${currentY + 20} L 340 ${currentY + 20}" stroke="#000" stroke-width="1.5" fill="none"/>
                    <circle cx="340" cy="${currentY + 20}" r="12" fill="#fff" stroke="#000" stroke-width="1.5" title="Role Grouping Node"/>
                    <path d="M 352 ${currentY + 20} L 370 ${currentY + 20}" stroke="#000" stroke-width="1.5" fill="none"/>
                    <g transform="translate(370, ${currentY})">
                        <rect width="${attrOvalW}" height="42" rx="21" fill="#fff2cc" stroke="#d6b656" stroke-width="1.5"/>
                        <text x="14" y="25" font-size="11" font-weight="bold" fill="#000">${escapeHtml(attr.type_name)}</text>
                    </g>
                    <path d="M ${370 + attrOvalW} ${currentY + 20} L ${valBoxX} ${currentY + 20}" stroke="#000" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>
                    <g transform="translate(${valBoxX}, ${currentY})">
                        <rect width="${valBoxW}" height="42" rx="3" fill="#a4c2f4" stroke="#337ab7" stroke-width="1.5"/>
                        <text x="8" y="16" font-size="10" font-weight="bold" fill="#000">${attr.concept_id}</text>
                        <text x="8" y="31" font-size="11" font-weight="600" fill="#000">${escapeHtml(attr.term)}</text>
                    </g>
                `;
                currentY += 55;
            });
        }

        const totalHeight = Math.max(400, currentY + 40);

        const svgCode = `
            <svg class="diagram-svg" viewBox="0 0 ${maxCanvasWidth} ${totalHeight}" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#000" />
                    </marker>
                </defs>
                <g transform="translate(20, 36)">
                    <rect width="${mainCardWidth}" height="48" rx="3" fill="#b3c6e7" stroke="#337ab7" stroke-width="2"/>
                    <text x="10" y="18" font-size="10" font-weight="bold" fill="#000">${sctid}</text>
                    <text x="10" y="34" font-size="12" font-weight="bold" fill="#000">${escapeHtml(titleTerm)}</text>
                </g>
                <path d="M ${20 + mainCardWidth} 60 L 270 60" stroke="#000" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>
                <g transform="translate(270, 44)">
                    <circle cx="16" cy="16" r="15" fill="#fff" stroke="#000" stroke-width="1.5"/>
                    <text x="9" y="22" font-size="16" font-weight="bold" fill="#000">≡</text>
                </g>
                ${nodesHtml}
            </svg>
        `;

        diagramCanvasContainer.innerHTML = svgCode;
    }

    // Download Diagram Handler
    downloadDiagramBtn.addEventListener('click', () => {
        const svg = diagramCanvasContainer.querySelector('svg');
        if (!svg) return;
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
        const svgUrl = URL.createObjectURL(svgBlob);
        const downloadLink = document.createElement('a');
        downloadLink.href = svgUrl;
        downloadLink.download = `snomed_diagram_${selectedConceptId || 'concept'}.svg`;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    });

    // Suggest Thai Synonym Modal Handler (Connected to Cloud Firestore)
    const btnAddSynonym          = document.getElementById('btnAddSynonym');
    const addSynonymModal        = document.getElementById('addSynonymModal');
    const closeSynonymModalBtn   = document.getElementById('closeSynonymModalBtn');
    const cancelSynonymBtn       = document.getElementById('cancelSynonymBtn');
    const saveSynonymBtn         = document.getElementById('saveSynonymBtn');
    const modalConceptIdSpan     = document.getElementById('modalConceptIdSpan');
    const modalConceptNameDiv    = document.getElementById('modalConceptNameDiv');
    const synonymInputText       = document.getElementById('synonymInputText');
    const synonymSubmitterInput  = document.getElementById('synonymSubmitterInput');
    const synonymNoteInput       = document.getElementById('synonymNoteInput');
    const synonymModalStatus     = document.getElementById('synonymModalStatus');

    if (btnAddSynonym) {
        btnAddSynonym.addEventListener('click', () => {
            if (!selectedConceptId) {
                alert('กรุณาเลือก Concept ในตารางก่อนทำการเสนอคำพ้อง');
                return;
            }
            modalConceptIdSpan.textContent = selectedConceptId;
            if (modalConceptNameDiv) {
                modalConceptNameDiv.textContent = currentConceptData?.display_name || currentConceptData?.snomed_preferred_term || '';
            }
            synonymInputText.value = '';
            if (synonymSubmitterInput) synonymSubmitterInput.value = '';
            if (synonymNoteInput) synonymNoteInput.value = '';
            synonymModalStatus.textContent = '';
            addSynonymModal.classList.remove('hidden');
            synonymInputText.focus();
        });
    }

    function closeSynModal() {
        if (addSynonymModal) addSynonymModal.classList.add('hidden');
    }

    if (closeSynonymModalBtn) closeSynonymModalBtn.addEventListener('click', closeSynModal);
    if (cancelSynonymBtn) cancelSynonymBtn.addEventListener('click', closeSynModal);

    if (saveSynonymBtn) {
        saveSynonymBtn.addEventListener('click', async () => {
            const val = (synonymInputText.value || '').trim();
            const submitter = (synonymSubmitterInput?.value || '').trim() || 'สัตวแพทย์ (KAHIS User)';
            const note = (synonymNoteInput?.value || '').trim();

            if (!val) {
                synonymModalStatus.textContent = 'กรุณากรอกคำพ้องภาษาไทยอย่างน้อย 1 คำ';
                return;
            }

            saveSynonymBtn.disabled = true;
            saveSynonymBtn.textContent = '⏳ กำลังส่งข้อมูล...';
            synonymModalStatus.textContent = '';

            try {
                // Save to Firebase Firestore collection 'ku_synonyms'
                if (firestoreDb) {
                    await firestoreDb.collection('ku_synonyms').add({
                        concept_id: String(selectedConceptId),
                        synonym_text: val,
                        lang_tag: 'ku',
                        status: 'pending',
                        submitted_by: submitter,
                        clinical_note: note,
                        created_at: new Date().toISOString()
                    });
                } else {
                    // Fallback to local server API if running on localhost
                    await fetch('/api/ku_synonym/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({concept_id: selectedConceptId, text: val, lang: 'ku'})
                    });
                }

                // Add to UI immediately as pending
                const li = document.createElement('li');
                li.className = 'desc-item';
                li.innerHTML = `<span class="desc-type-badge desc-badge-syn" style="background:#fef3c7; color:#b45309; border:1px solid #fde68a;">Pending</span> <span class="desc-lang desc-lang-ku">ku</span> <span class="desc-text" style="font-weight:600; color:#10b981;">${escapeHtml(val)}</span> <small style="color:#64748b; font-size:11px; margin-left:4px;">(รออนุมัติ)</small>`;
                synonymListUl.appendChild(li);

                closeSynModal();
                alert(`✅ ส่งข้อเสนอคำพ้อง "${val}" เรียบร้อยแล้ว!\nข้อมูลถูกบันทึกขึ้น Cloud Firestore (สถานะ Pending) เพื่อรอการตรวจสอบและบรรจุเข้าฐานข้อมูลรอบถัดไป`);
            } catch (err) {
                console.error('Save synonym error:', err);
                synonymModalStatus.textContent = 'เกิดข้อผิดพลาดในการบันทึก: ' + err.message;
            } finally {
                saveSynonymBtn.disabled = false;
                saveSynonymBtn.textContent = '🚀 ส่งข้อเสนอคำพ้อง';
            }
        });
    }

    // ===== USER GUIDE MODAL =====
    const openUserGuideBtn    = document.getElementById('openUserGuideBtn');
    const userGuideModal      = document.getElementById('userGuideModal');
    const closeUserGuideBtn   = document.getElementById('closeUserGuideBtn');
    const dismissUserGuideBtn = document.getElementById('dismissUserGuideBtn');

    if (openUserGuideBtn && userGuideModal) {
        openUserGuideBtn.addEventListener('click', (e) => {
            e.preventDefault();
            userGuideModal.classList.remove('hidden');
        });

        const hideUserGuideModal = () => userGuideModal.classList.add('hidden');

        if (closeUserGuideBtn)   closeUserGuideBtn.addEventListener('click', hideUserGuideModal);
        if (dismissUserGuideBtn) dismissUserGuideBtn.addEventListener('click', hideUserGuideModal);

        userGuideModal.addEventListener('click', (e) => {
            if (e.target === userGuideModal) {
                hideUserGuideModal();
            }
        });
    }

    // Helper
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function loadFirestorePendingSynonyms(conceptId) {
        if (!firestoreDb || !conceptId) return;
        firestoreDb.collection('ku_synonyms')
            .where('concept_id', '==', String(conceptId))
            .get()
            .then(snapshot => {
                snapshot.forEach(doc => {
                    const data = doc.data();
                    if (!data.synonym_text) return;
                    const existing = Array.from(synonymListUl.querySelectorAll('.desc-text'))
                        .some(el => el.textContent.trim().toLowerCase() === data.synonym_text.trim().toLowerCase());
                    if (!existing) {
                        const li = document.createElement('li');
                        li.className = 'desc-item';
                        const isPending = data.status === 'pending';
                        const badgeText = isPending ? 'Pending' : 'Synonym';
                        const badgeStyle = isPending ? 'background:#fef3c7; color:#b45309; border:1px solid #fde68a;' : '';
                        li.innerHTML = `<span class="desc-type-badge desc-badge-syn desc-badge-ku" style="${badgeStyle}">${escapeHtml(badgeText)}</span> <span class="desc-lang desc-lang-ku">ku</span> <span class="desc-text-ku">${escapeHtml(data.synonym_text)}</span> <small style="color:#cbd5e1; font-size:11px; margin-left:4px;">(${isPending ? 'รออนุมัติ' : 'อนุมัติแล้ว'})</small>`;
                        synonymListUl.appendChild(li);
                    }
                });
            })
            .catch(err => console.log('Firestore fetch notice:', err));
    }
    window.loadConceptDetails = loadConceptDetails;
});


