/**
 * static/app.js
 * Client-side JavaScript for SA-PDT & SNOMED CT Veterinary Extension for KAHIS.
 * Implements Search History (localStorage), Action Icons alignment, and Dynamic Concept Search.
 */

document.addEventListener('DOMContentLoaded', () => {
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
    let currentStatusMode = 'active';
    let selectedSemanticTypes = new Set(['disorder', 'finding']);

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
                
                const prefix = btn.textContent.split(':')[0];
                btn.textContent = `${prefix}: ${text} ▾`;
                panel.classList.add('hidden');

                if (onSelectCallback) onSelectCallback(val);
            });
        });
    }

    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-panel').forEach(p => p.classList.add('hidden'));
    });

    setupCustomDropdown('searchModeDropdownBtn', 'searchModePanel', () => {
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('statusDropdownBtn', 'statusPanel', (val) => {
        currentStatusMode = val;
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('descTypeDropdownBtn', 'descTypePanel', () => {
        currentPage = 1;
        performSearch();
    });

    setupCustomDropdown('langRefsetDropdownBtn', 'langRefsetPanel', () => {
        currentPage = 1;
        performSearch();
    });

    // 3. Setup Semantic Checkbox Change Listeners
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

    // 4. Initial Setup
    initFiltersAndVersions();
    performSearch();

    // 5. Under Construction Toast Popup
    function showUnderConstructionToast() {
        toastPopup.classList.remove('hidden');
        setTimeout(() => {
            toastPopup.classList.add('hidden');
        }, 2500);
    }

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
        try {
            const res = await fetch('/api/filters');
            const data = await res.json();

            if (data.release_versions) {
                badgeSapdt.textContent = data.release_versions.sapdt || 'SA-PDT 20260331';
                badgeVsct.textContent = data.release_versions.vsct || 'VSCT 20260331';
                badgeSct.textContent = data.release_versions.sct || 'SCT 20260701';
            }
        } catch (err) {
            console.error('Failed to load filters:', err);
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
        const params = new URLSearchParams({
            q: currentQuery,
            status: currentStatusMode,
            group_by_concept: isGroupByConcept ? 'true' : 'false',
            limit: pageSize,
            offset: offset
        });

        Array.from(selectedSemanticTypes).forEach(st => params.append('semantic_type', st));

        if (!currentQuery) {
            totalResults = 0;
            matchCountBar.textContent = '0 matches found in 0.00 seconds.';
            resultsTableBody.innerHTML = '';
            updateSemanticCountBadges({});
            updatePagination();
            return;
        }

        // Save query to search history
        saveQueryToSearchHistory(currentQuery);

        resultsTableBody.innerHTML = '<tr><td colspan="2" class="empty-msg">Searching...</td></tr>';

        try {
            const res = await fetch(`/api/search?${params}`);
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
                ? '<span class="icon-menu" title="Fully Defined Concept">≡</span>'
                : '<span class="icon-circle" title="Primitive Concept">○</span>';

            const isAct = (item.in_sapdt === 'Yes' && item.sapdt_status === 'Active') ||
                          (item.in_vsct === 'Yes' && item.snomed_active === 'Yes');
            const inactiveBadge = (!isAct && currentStatusMode === 'all')
                ? ' <span class="source-badge-micro micro-inactive">Inactive</span>'
                : '';

            tr.innerHTML = `
                <td class="term-col">${iconHtml} ${escapeHtml(item.display_name)}${inactiveBadge}</td>
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

        try {
            const res = await fetch(`/api/concept/${conceptId}`);
            if (!res.ok) throw new Error('Concept not found');

            const data = await res.json();
            currentConceptData = data;
            
            const termStr = data.display_name || data.snomed_preferred_term || conceptId;
            saveConceptToHistory(conceptId, termStr);

            renderConceptDetails(data);
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
            dbBadgesRow.innerHTML += '<span class="db-badge-pill">SA-PDT</span>';
        }
        if (data.in_vsct === 'Yes') {
            dbBadgesRow.innerHTML += '<span class="db-badge-pill">VSCT</span>';
        }
        if (data.in_sct_inter === 'Yes') {
            dbBadgesRow.innerHTML += '<span class="db-badge-pill">SCT-Inter</span>';
        }

        conceptFsnFull.textContent = `${data.concept_id} | ${data.snomed_fsn || titleTerm} |`;

        // Synonyms & Descriptions — SCT-01 FIX + CONFLICT-04 FIX
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
                if (d.type === 'ku')        badgeClass = 'desc-badge-syn';

                let badgeText = d.type === 'ku' ? 'Synonym' : d.type;
                let langClass = d.type === 'ku' ? 'desc-lang desc-lang-ku' : 'desc-lang';
                let textStyle = d.type === 'ku' ? 'style="font-weight:600; color:#10b981;"' : '';

                li.innerHTML = `<span class="desc-type-badge ${badgeClass}">${escapeHtml(badgeText)}</span> <span class="${langClass}">${escapeHtml(d.lang || 'en')}</span> <span class="desc-text" ${textStyle}>${escapeHtml(d.text)}</span>`;
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

    // Add Synonym UI Modal Handler
    const btnAddSynonym = document.getElementById('btnAddSynonym');
    const addSynonymModal = document.getElementById('addSynonymModal');
    const closeSynonymModalBtn = document.getElementById('closeSynonymModalBtn');
    const cancelSynonymBtn = document.getElementById('cancelSynonymBtn');
    const saveSynonymBtn = document.getElementById('saveSynonymBtn');
    const modalConceptIdSpan = document.getElementById('modalConceptIdSpan');
    const synonymInputText = document.getElementById('synonymInputText');
    const synonymPinInput = document.getElementById('synonymPinInput');
    const synonymModalStatus = document.getElementById('synonymModalStatus');

    if (btnAddSynonym) {
        btnAddSynonym.addEventListener('click', () => {
            if (!selectedConceptId) {
                alert('กรุณาเลือก Concept ก่อนทำการเพิ่มคำพ้อง');
                return;
            }
            modalConceptIdSpan.textContent = selectedConceptId;
            synonymInputText.value = '';
            if (synonymPinInput) synonymPinInput.value = '';
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
            const pin = (synonymPinInput ? synonymPinInput.value : '').trim();

            if (!val) {
                synonymModalStatus.textContent = 'กรุณากรอกคำพ้องอย่างน้อย 1 คำ';
                return;
            }
            if (pin !== '53027918') {
                synonymModalStatus.textContent = 'รหัส PIN ไม่ถูกต้อง';
                return;
            }

            saveSynonymBtn.disabled = true;
            saveSynonymBtn.textContent = '⏳ กำลังบันทึก...';
            try {
                const resp = await fetch('/api/ku_synonym/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({concept_id: selectedConceptId, text: val, lang: 'ku'})
                });
                const res = await resp.json();
                if (res.ok) {
                    closeSynModal();
                    loadConceptDetails(selectedConceptId);
                } else {
                    synonymModalStatus.textContent = res.error || 'เกิดข้อผิดพลาดในการบันทึก';
                }
            } catch (err) {
                synonymModalStatus.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้';
            } finally {
                saveSynonymBtn.disabled = false;
                saveSynonymBtn.textContent = '💾 บันทึกคำพ้อง';
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

    window.loadConceptDetails = loadConceptDetails;
});
