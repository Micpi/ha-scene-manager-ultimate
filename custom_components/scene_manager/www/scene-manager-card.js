// -------------------------------------------------------------------
// SCENE MANAGER ULTIMATE
// Version: 1.0.5
// Description: Carte de gestion de scènes avec Drag&Drop et Sync Serveur
// -------------------------------------------------------------------

console.info(
    `%c SCENE-MANAGER-ULTIMATE %c v1.0.5 `,
    'color: white; background: #4CAF50; font-weight: 700;',
    'color: #4CAF50; background: white; font-weight: 700;'
);

// Version constant used below
const VERSION = '1.0.5';

// ... Le reste du code de la classe SceneManagerCard ...

console.info(
    `%c SCENE-MANAGER %c ${VERSION} `,
    'color: white; background: #03a9f4; font-weight: 700;',
    'color: #03a9f4; background: white; font-weight: 700;'
);

window.customCards = window.customCards || [];
window.customCards.push({
    type: "scene-manager-card",
    name: "Scene Manager Ultimate",
    description: "Interface tactile de gestion de scènes pour Home Assistant.",
    preview: true
});

const PRESET_ICONS = [
    "mdi:palette", "mdi:sofa", "mdi:bed", "mdi:power-sleep", "mdi:weather-sunny",
    "mdi:fire", "mdi:snowflake", "mdi:water-percent", "mdi:leaf", "mdi:heart",
    "mdi:candle", "mdi:ghost", "mdi:movie", "mdi:gamepad-variant", "mdi:book-open-variant",
    "mdi:music", "mdi:party-popper", "mdi:silverware-fork-knife", "mdi:glass-cocktail", "mdi:coffee",
    "mdi:briefcase", "mdi:laptop", "mdi:pencil", "mdi:eye-off", "mdi:chef-hat",
    "mdi:shower", "mdi:toilet", "mdi:baby-carriage", "mdi:tshirt-crew", "mdi:car",
    "mdi:circle", "mdi:circle-outline", "mdi:home-group"
];

class SceneManagerCard extends HTMLElement {
    static getConfigElement() { return document.createElement("scene-manager-editor"); }
    static getStubConfig() { return { title: "Mes Scènes", icon: "mdi:home-floor-1", button_style: "filled", button_shape: "rounded", scene_alignment: "left", button_width: "100px", button_height: "80px" }; }

    set hass(hass) {
        this._hass = hass;

        if (!this.shadowRoot) {
            this.attachShadow({ mode: 'open' });
            this._initElements();
        }

        if (this.content) {
            this._checkServerUpdates();

            if (this.isMenuOpen) {
                if (this.mainLightsContainer && this.mainLightsContainer.innerHTML === "") {
                    if (this.areas.length > 0) this._buildLightControls(this.editingId ? this._getSceneEntities(this.editingId) : null);
                }
                this._updateLightStates();
            }

            if (this.shouldUpdate) {
                this._updateContent();
                this.shouldUpdate = false;
            }
        }
    }

    setConfig(config) {
        this.config = config;
        const oldFixed = this.fixedRoom;
        this.fixedRoom = config.room ? config.room.toLowerCase() : null;
        this.btnWidth = config.button_width || '100px';
        this.btnHeight = config.button_height || '80px';
        this.alignment = 'flex-start';
        if (config.scene_alignment === 'center') this.alignment = 'center';
        if (config.scene_alignment === 'right') this.alignment = 'flex-end';

        if (this.shadowRoot) {
            const list = this.shadowRoot.getElementById("sceneList");
            if (list) list.style.justifyContent = this.alignment;

            if (oldFixed !== this.fixedRoom || this.lastTitle !== config.title) {
                this._renderHeader();
                this.lastTitle = config.title;
                if (this.fixedRoom) {
                    this.currentRoom = this.fixedRoom;
                } else {
                    this._fetchData();
                }
            }
            this.shouldUpdate = true;
        }
    }

    _initElements() {
        this.currentIcon = "mdi:palette";
        this.currentColor = "#9E9E9E";
        this.isMenuOpen = false;
        this.editingId = null;
        this.dragSrcEl = null;
        this.currentRoom = this.fixedRoom || "";
        this.areas = [];
        this.entitiesRegistry = [];
        this.cachedOrder = [];
        this.cachedMeta = {};
        this.shouldUpdate = true;
        this._lastStorageUpdate = null;

        this.shadowRoot.innerHTML = `
        <style>
          ha-card { 
            padding: 0; display: flex; flex-direction: column; 
            background: none; box-shadow: none; border: none;
            font-family: var(--paper-font-body1_-_font-family);
          }
          .control-bar { display: flex; align-items: center; gap: 12px; background: transparent; padding: 4px 16px 12px 16px; box-shadow: none; border: none; }
          .header-icon { --mdc-icon-size: 28px; color: var(--primary-color); opacity: 0.9; }
          .fixed-title { flex: 1; font-size: 22px; font-weight: 500; letter-spacing: 0.5px; color: var(--primary-text-color); display: flex; align-items: center; font-family: var(--paper-font-headline_-_font-family); }
          select.room-selector { flex: 1; padding: 0; font-size: 22px; font-weight: 500; letter-spacing: 0.5px; border: none; background: transparent; color: var(--primary-text-color); cursor: pointer; outline: none; font-family: var(--paper-font-headline_-_font-family); -webkit-appearance: none; -moz-appearance: none; appearance: none; }
          select.room-selector option { background-color: var(--card-background-color, #202020); color: var(--primary-text-color, #ffffff); }
          .toggle-btn { cursor: pointer; color: var(--primary-text-color); opacity: 0.6; transition: all 0.3s; background: transparent; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid transparent; }
          .toggle-btn:hover { background: rgba(var(--rgb-primary-color), 0.1); color: var(--primary-color); opacity: 1; }
          .toggle-btn.active { background: rgba(255, 0, 0, 0.1); color: #f44336; opacity: 1; transform: rotate(0deg); }
          .toggle-btn.save-mode { background: #4CAF50; color: white; opacity: 1; box-shadow: 0 2px 8px rgba(76, 175, 80, 0.4); }
          .scene-list { display: flex; gap: 12px; overflow-x: auto; padding: 4px 16px 25px 16px; scroll-behavior: smooth; scrollbar-width: none; min-height: calc(${this.btnHeight} + 10px); scroll-snap-type: x mandatory; justifyContent: ${this.alignment}; }
          .scene-list::-webkit-scrollbar { display: none; }
          .scene-btn { position: relative; color: var(--primary-text-color); cursor: pointer; text-align: center; font-weight: 500; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; min-width: ${this.btnWidth}; width: ${this.btnWidth}; height: ${this.btnHeight}; flex-shrink: 0; scroll-snap-align: start; transition: transform 0.1s ease-in-out, background 0.3s, border-color 0.3s, color 0.3s, box-shadow 0.3s; user-select: none; box-sizing: border-box; --btn-icon-color: var(--primary-text-color); }
          #creationArea { max-height: 0; overflow: hidden; transition: max-height 0.4s ease-out, opacity 0.3s ease-out, margin 0.3s; opacity: 0; background: var(--card-background-color, white); border-radius: 16px; margin-top: 0px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid transparent; }
          #creationArea.open { max-height: 800px; opacity: 1; padding: 16px; margin-top: 0px; border: 1px solid var(--divider-color, #eee); overflow-y: auto; }
          .scene-btn.being-edited { border: 2px solid #4CAF50 !important; box-shadow: 0 0 15px rgba(76, 175, 80, 0.5) !important; transform: scale(0.98); }
          .color-wrapper { position: relative; width: 48px; height: 48px; flex-shrink: 0; border-radius: 50%; overflow: hidden; border: 1px solid var(--divider-color, #ccc); cursor: pointer; box-sizing: border-box; }
          input[type="color"] { -webkit-appearance: none; border: none; width: 200%; height: 200%; cursor: pointer; transform: translate(-25%, -25%); padding: 0; background: none; }
          .input-row { display: flex; gap: 10px; margin-bottom: 15px; align-items: center; margin-top: 15px; }
          input[type=text] { flex: 1; height: 48px; padding: 0 12px; border: 1px solid var(--divider-color, #ccc); background: var(--secondary-background-color); color: var(--primary-text-color); border-radius: 8px; font-size: 16px; box-sizing: border-box; }
          button.save-btn-action { background-color: var(--primary-color, #03a9f4); color: white; border: none; border-radius: 8px; height: 48px; width: 48px; min-width: 48px; padding: 0; cursor: pointer; font-weight: bold; font-size: 24px; transition: background 0.3s; display: flex; align-items: center; justify-content: center; }
          button.save-btn-action.save-mode { background-color: #4CAF50; }
          .style-filled { background: var(--secondary-background-color, #eee); border: 1px solid var(--divider-color, #eee); box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
          .style-outline { background: transparent; border: 2px solid var(--btn-icon-color); color: var(--primary-text-color); }
          .style-ghost { background: transparent; border: 1px solid transparent; }
          .shape-rounded { border-radius: 16px; }
          .shape-box { border-radius: 8px; }
          .shape-circle { border-radius: 50%; width: ${this.btnWidth}; height: ${this.btnWidth}; }
          .scene-btn ha-icon { pointer-events: none; color: var(--btn-icon-color); transition: color 0.3s; } 
          .scene-btn span { width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; pointer-events: none; }
          .scene-btn:active { transform: scale(0.92); }
          .scene-btn.activated { border-color: #4CAF50; box-shadow: 0 0 10px rgba(76, 175, 80, 0.2); }
          .scene-btn.activated ha-icon { color: #4CAF50 !important; transform: scale(1.2); }
          .scene-btn.dragging { opacity: 0.4; border: 2px dashed var(--primary-color); transform: scale(0.95); }
          .scene-btn.over { border: 2px solid var(--primary-color); transform: scale(1.05); }
          .action-badge { position: absolute; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.3); opacity: 0; transform: scale(0); transition: all 0.3s; pointer-events: auto; z-index: 10; cursor: pointer; color: white; }
          .delete-badge { top: -6px; right: -6px; background-color: #f44336; }
          .edit-badge { bottom: -8px; left: 50%; transform: translateX(-50%) scale(0); background-color: var(--primary-color, #03a9f4); }
          .shape-circle .delete-badge { top: 0; right: 0; } .shape-circle .edit-badge { bottom: 0; }
          .scene-list.edit-mode .action-badge { opacity: 1; transform: scale(1); }
          .scene-list.edit-mode .edit-badge { opacity: 1; transform: translateX(-50%) scale(1); }
          .empty { margin: auto; color: var(--secondary-text-color); padding: 10px; font-style: italic; }
          details { margin-bottom: 8px; border: 1px solid var(--divider-color, #eee); border-radius: 8px; overflow: hidden; }
          summary { background: rgba(var(--rgb-primary-color), 0.05); padding: 10px 15px; cursor: pointer; list-style: none; display: flex; align-items: center; gap: 10px; font-weight: bold; font-size: 14px; }
          summary::-webkit-details-marker { display: none; }
          .room-checkbox { width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary-color); }
          .room-title { flex: 1; }
          .summary-arrow::after { content: '▼'; font-size: 10px; transition: transform 0.2s; display:block; }
          details[open] .summary-arrow::after { transform: rotate(180deg); }
          .room-content { padding: 5px 10px 10px 10px; display: flex; flex-direction: column; gap: 6px; }
          .light-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; border-bottom: 1px dashed #eee; }
          .light-row:last-child { border-bottom: none; }
          .light-select { width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary-color); margin-left: 10px; }
          .light-name { font-size: 13px; font-weight: 500; width: 110px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
          input[type=range] { flex: 1; -webkit-appearance: none; height: 6px; border-radius: 3px; background: #ddd; outline: none; }
          input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--primary-color); cursor: pointer; }
          .light-toggle { cursor: pointer; color: var(--disabled-text-color, #bdbdbd); }
          .light-toggle.on { color: var(--primary-color, #ff9800); }
          .icon-picker { display: flex; gap: 10px; overflow-x: auto; padding: 8px 4px 15px 4px; scrollbar-width: thin; }
          .icon-option { background: var(--secondary-background-color, #eee); color: var(--primary-text-color); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; border: 2px solid transparent; transition: all 0.2s; }
          .icon-option.selected { background: var(--card-background-color, white); color: var(--primary-color); border-color: var(--primary-color); transform: scale(1.15); box-shadow: 0 3px 6px rgba(0,0,0,0.2); }
        </style>
        
        <ha-card>
          <div id="headerContainer"></div>
          <div class="scene-list" id="sceneList"></div>
          <div id="creationArea">
            <div id="mainLightsContainer"></div>
            <div class="icon-picker" id="iconList"></div>
            <div class="input-row">
              <div class="color-wrapper" title="Couleur du bouton">
                <input type="color" id="sceneColor" value="#9E9E9E">
              </div>
              <input type="text" id="newSceneName" placeholder="Nom de la scène...">
              <button class="add-btn save-btn-action" id="saveBtn">
                 <ha-icon icon="mdi:content-save-plus"></ha-icon>
              </button>
            </div>
          </div>
        </ha-card>
      `;

        this.content = this.shadowRoot.getElementById("sceneList");
        this.headerContainer = this.shadowRoot.getElementById("headerContainer");
        this.iconList = this.shadowRoot.getElementById("iconList");
        this.inputName = this.shadowRoot.getElementById("newSceneName");
        this.inputColor = this.shadowRoot.getElementById("sceneColor");
        this.saveBtn = this.shadowRoot.getElementById("saveBtn");
        this.creationArea = this.shadowRoot.getElementById("creationArea");
        this.mainLightsContainer = this.shadowRoot.getElementById("mainLightsContainer");

        this._renderHeader();
        this._renderIconPicker();
        this._fetchData();

        this.saveBtn.addEventListener("click", () => this._saveScene());
    }

    _renderHeader() {
        const headerIcon = this.config.icon || "mdi:home-floor-1";
        const showIcon = this.config.show_icon !== false;
        const title = this.config.title || (this.fixedRoom ? "" : "Mes Scènes");

        let headerContent = '';
        if (this.fixedRoom) {
            headerContent = `
            <div class="control-bar">
                ${showIcon ? `<ha-icon icon="${headerIcon}" class="header-icon"></ha-icon>` : ''}
                <div class="fixed-title"><span id="fixedRoomName">${title}</span></div>
                <div class="toggle-btn" id="toggleMenuBtn"><ha-icon icon="mdi:plus" id="toggleIcon"></ha-icon></div>
            </div>
          `;
        } else {
            headerContent = `
             <div class="control-bar">
                ${showIcon ? `<ha-icon icon="${headerIcon}" class="header-icon"></ha-icon>` : ''}
                <select class="room-selector" id="roomSelector">
                    <option value="" disabled selected>Chargement...</option>
                </select>
                <div class="toggle-btn" id="toggleMenuBtn"><ha-icon icon="mdi:plus" id="toggleIcon"></ha-icon></div>
             </div>
          `;
        }

        this.headerContainer.innerHTML = headerContent;
        this.toggleBtn = this.shadowRoot.getElementById("toggleMenuBtn");
        this.toggleIcon = this.shadowRoot.getElementById("toggleIcon");
        this.roomSelector = this.shadowRoot.getElementById("roomSelector");

        if (this.toggleBtn) this.toggleBtn.addEventListener("click", () => this._toggleMenu());
        if (this.roomSelector && this.areas.length > 0) this._populateRoomSelector();
    }

    _populateRoomSelector() {
        this.roomSelector.innerHTML = "";
        this.areas.forEach(area => {
            const option = document.createElement("option");
            option.value = area.area_id; option.innerText = area.name;
            if (area.area_id === this.currentRoom.toLowerCase()) option.selected = true;
            this.roomSelector.appendChild(option);
        });
        this.roomSelector.addEventListener("change", (e) => {
            this.currentRoom = e.target.value;
            this._updateStorageEntity();
            this.shouldUpdate = true;
            this._updateContent();
            this.mainLightsContainer.innerHTML = "";
            localStorage.setItem('scene_manager_last_room', this.currentRoom);
        });
    }

    async _fetchData() {
        try {
            const areas = await this._hass.callWS({ type: 'config/area_registry/list' });
            this.areas = areas.sort((a, b) => a.name.localeCompare(b.name));
            const entities = await this._hass.callWS({ type: 'config/entity_registry/list' });
            this.entitiesRegistry = entities;

            if (!this.fixedRoom) {
                const lastRoom = localStorage.getItem('scene_manager_last_room');
                if (lastRoom) this.currentRoom = lastRoom;
                if (!this.currentRoom && this.areas.length > 0) this.currentRoom = this.areas[0].area_id;
                if (this.roomSelector) this._populateRoomSelector();
            } else {
                this.currentRoom = this.fixedRoom;
                const titleSpan = this.shadowRoot.getElementById("fixedRoomName");
                if (titleSpan && !this.config.title) {
                    const area = this.areas.find(a => a.area_id === this.fixedRoom);
                    titleSpan.innerText = area ? area.name : this.fixedRoom.toUpperCase();
                }
            }
            this.shouldUpdate = true;
            this._updateContent();
        } catch (e) { console.error("Erreur", e); }
    }

    _getStorageEntityId() { return `sensor.scene_manager_data_${this.currentRoom.replace(/[^a-z0-9_]/g, '_')}`; }

    _checkServerUpdates() {
        if (!this.currentRoom) return;
        const entityId = this._getStorageEntityId();
        const stateObj = this._hass.states[entityId];
        if (stateObj && stateObj.last_updated !== this._lastStorageUpdate) {
            this._lastStorageUpdate = stateObj.last_updated;
            if (stateObj.attributes) {
                this.cachedOrder = stateObj.attributes.order || [];
                this.cachedMeta = stateObj.attributes.meta || {};
                this.shouldUpdate = true;
            }
        }
    }

    _pushToServer() {
        const entityId = this._getStorageEntityId();
        this._hass.callService("python_script", "set_state", {
            entity_id: entityId, state: Date.now().toString(), attributes: { order: this.cachedOrder, meta: this.cachedMeta }
        });
        this._lastStorageUpdate = "Just Updated";
    }
    _updateStorageEntity() { this._checkServerUpdates(); }
    _saveOrder(orderedIds) { this.cachedOrder = orderedIds; this._pushToServer(); }
    _loadOrder() { return this.cachedOrder; }
    _saveMeta(meta) { this.cachedMeta = meta; this._pushToServer(); }
    _loadMeta() { return this.cachedMeta; }
    _getSceneEntities(sceneId) { const sceneObj = this._hass.states[sceneId]; return sceneObj && sceneObj.attributes.entity_id ? sceneObj.attributes.entity_id : []; }

    _buildLightControls(entitiesInScene = null) {
        if (!this.isMenuOpen) return;
        const allLights = Object.keys(this._hass.states).filter((eid) => eid.startsWith("light."));
        const lightsByArea = {}; this.areas.forEach(a => lightsByArea[a.area_id] = []); const noAreaLights = [];

        allLights.forEach(eid => {
            let assigned = false; const entry = this.entitiesRegistry.find(e => e.entity_id === eid);
            if (entry && entry.area_id && lightsByArea[entry.area_id]) { lightsByArea[entry.area_id].push(eid); assigned = true; }
            if (!assigned) {
                const stateObj = this._hass.states[eid];
                const friendlyName = stateObj ? stateObj.attributes.friendly_name || "" : "";
                for (const area of this.areas) {
                    if (eid.toLowerCase().includes(area.area_id.toLowerCase()) || friendlyName.toLowerCase().includes(area.name.toLowerCase())) { lightsByArea[area.area_id].push(eid); assigned = true; break; }
                }
            }
            if (!assigned) noAreaLights.push(eid);
        });

        this.mainLightsContainer.innerHTML = "";
        const createSection = (areaName, areaId, lights, startOpen) => {
            const details = document.createElement("details"); if (startOpen) details.open = true;
            const summary = document.createElement("summary");
            const masterCheck = document.createElement("input"); masterCheck.type = "checkbox"; masterCheck.className = "room-checkbox";
            masterCheck.addEventListener("click", (e) => { e.stopPropagation(); const checkboxes = container.querySelectorAll(".light-select"); checkboxes.forEach(cb => cb.checked = masterCheck.checked); });
            const title = document.createElement("span"); title.className = "room-title"; title.innerText = areaName;
            const arrow = document.createElement("span"); arrow.className = "summary-arrow";
            summary.appendChild(masterCheck); summary.appendChild(title); summary.appendChild(arrow); details.appendChild(summary);
            const container = document.createElement("div"); container.className = "room-content";

            if (!lights || lights.length === 0) { container.innerHTML = `<div style="opacity:0.5; font-size:12px; font-style:italic; text-align:center;">Aucune lumière détectée</div>`; } else {
                lights.sort();
                lights.forEach(eid => {
                    const row = document.createElement("div"); row.className = "light-row"; row.dataset.entityId = eid;
                    row.innerHTML = `<input type="checkbox" class="light-select" data-entity="${eid}"><div class="light-name">...</div><input type="range" min="0" max="100" class="brightness-slider"><div class="light-toggle"><ha-icon icon="mdi:power"></ha-icon></div>`;
                    const cb = row.querySelector(".light-select");
                    cb.addEventListener("change", () => { const all = container.querySelectorAll(".light-select"); const checked = container.querySelectorAll(".light-select:checked"); masterCheck.checked = checked.length > 0; masterCheck.indeterminate = checked.length > 0 && checked.length < all.length; });
                    row.querySelector(".light-toggle").addEventListener("click", () => this._hass.callService("light", "toggle", { entity_id: eid }));
                    row.querySelector(".brightness-slider").addEventListener("change", (e) => { const val = e.target.value; if (val == 0) this._hass.callService("light", "turn_off", { entity_id: eid }); else this._hass.callService("light", "turn_on", { entity_id: eid, brightness_pct: val }); });
                    row.addEventListener("change", (e) => { if (e.target.classList.contains("brightness-slider")) { cb.checked = true; cb.dispatchEvent(new Event("change")); } });
                    container.appendChild(row);
                });
            }
            details.appendChild(container); this.mainLightsContainer.appendChild(details);
        };

        if (this.currentRoom) {
            const area = this.areas.find(a => a.area_id === this.currentRoom);
            const areaName = area ? area.name : this.currentRoom.toUpperCase();
            createSection(areaName, this.currentRoom, lightsByArea[this.currentRoom] || [], true);
            if (lightsByArea[this.currentRoom]) delete lightsByArea[this.currentRoom];
        }

        this.areas.forEach(area => {
            if (area.area_id !== this.currentRoom) {
                createSection(area.name, area.area_id, lightsByArea[area.area_id] || [], false);
            }
        });

        if (noAreaLights.length > 0) { createSection("Autres / Non Assignées", "unknown", noAreaLights, false); }

        if (entitiesInScene) { this.shadowRoot.querySelectorAll(".light-select").forEach(cb => { if (entitiesInScene.includes(cb.dataset.entity)) cb.checked = true; }); }
        this._updateLightStates(true);
    }

    _updateLightStates(firstRun = false) {
        if (!this.isMenuOpen) return;
        const rows = this.shadowRoot.querySelectorAll(".light-row");
        rows.forEach(row => {
            const eid = row.dataset.entityId; const stateObj = this._hass.states[eid]; if (!stateObj) return;
            const isDim = stateObj.attributes.supported_color_modes && !stateObj.attributes.supported_color_modes.includes("onoff");
            const isOn = stateObj.state === "on"; const brightness = stateObj.attributes.brightness ? Math.round((stateObj.attributes.brightness / 255) * 100) : 0;
            const name = stateObj.attributes.friendly_name || eid;
            row.querySelector(".light-name").innerText = name; row.querySelector(".light-name").title = name;
            const slider = row.querySelector(".brightness-slider"); slider.value = isOn ? brightness : 0; slider.disabled = !isDim && stateObj.attributes.brightness === undefined; if (slider.disabled) slider.style.opacity = 0.3; else slider.style.opacity = 1;
            const toggle = row.querySelector(".light-toggle"); if (isOn) toggle.classList.add("on"); else toggle.classList.remove("on");
            if (firstRun && !this.editingId) { if (eid.includes(this.currentRoom) && isOn) { const cb = row.querySelector(".light-select"); cb.checked = true; cb.dispatchEvent(new Event("change")); } }
        });
        this.shadowRoot.querySelectorAll("details").forEach(detail => { const master = detail.querySelector(".room-checkbox"); const all = detail.querySelectorAll(".light-select"); const checked = detail.querySelectorAll(".light-select:checked"); if (all.length > 0) { master.checked = checked.length > 0; master.indeterminate = checked.length > 0 && checked.length < all.length; } });
    }

    _startEditing(entityId, name, icon, color) {
        this.editingId = entityId; this.inputName.value = name; this.currentIcon = icon; this.inputColor.value = color || "#9E9E9E";
        this._renderIconPicker();
        this.saveBtn.innerHTML = `<ha-icon icon="mdi:content-save-edit"></ha-icon>`;
        this.saveBtn.classList.add("save-mode");
        if (!this.isMenuOpen) this._toggleMenu(true);
        const sceneObj = this._hass.states[entityId]; const entitiesInScene = sceneObj && sceneObj.attributes.entity_id ? sceneObj.attributes.entity_id : [];
        this._hass.callService("scene", "turn_on", { entity_id: entityId });
        this._buildLightControls(entitiesInScene); this._updateContent();
    }

    _stopEditing() {
        this.editingId = null;
        this.inputName.value = "";
        this.currentIcon = "mdi:palette";
        this.inputColor.value = "#9E9E9E";
        this.saveBtn.innerHTML = `<ha-icon icon="mdi:content-save-plus"></ha-icon>`;
        this.saveBtn.classList.remove("save-mode");
        this._updateToggleIcon();
        this._renderIconPicker(); this._buildLightControls(null); this._updateContent();
    }

    _updateToggleIcon() {
        if (this.isMenuOpen) {
            this.toggleIcon.setAttribute("icon", "mdi:close");
            this.toggleBtn.classList.add("active");
            this.toggleBtn.classList.remove("save-mode");
        } else {
            this.toggleIcon.setAttribute("icon", "mdi:plus");
            this.toggleBtn.classList.remove("active");
            this.toggleBtn.classList.remove("save-mode");
        }
    }

    _handleDragStart(e) { this.dragSrcEl = e.target.closest('.scene-btn'); this.dragSrcEl.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', this.dragSrcEl.dataset.entityId); }
    _handleDragOver(e) { if (e.preventDefault) e.preventDefault(); e.dataTransfer.dropEffect = 'move'; const target = e.target.closest('.scene-btn'); if (target && target !== this.dragSrcEl) target.classList.add('over'); return false; }
    _handleDragLeave(e) { const target = e.target.closest('.scene-btn'); if (target) target.classList.remove('over'); }
    _handleDrop(e) { if (e.stopPropagation) e.stopPropagation(); if (e.preventDefault) e.preventDefault(); const target = e.target.closest('.scene-btn'); this.shadowRoot.querySelectorAll('.scene-btn').forEach(col => { col.classList.remove('over'); col.classList.remove('dragging'); }); if (this.dragSrcEl && target && this.dragSrcEl !== target) { const srcId = this.dragSrcEl.dataset.entityId; const targetId = target.dataset.entityId; const allBtns = Array.from(this.shadowRoot.querySelectorAll(".scene-btn")); let order = allBtns.map(b => b.dataset.entityId); const srcIndex = order.indexOf(srcId); const targetIndex = order.indexOf(targetId); if (srcIndex > -1 && targetIndex > -1) { order.splice(srcIndex, 1); order.splice(targetIndex, 0, srcId); this._saveOrder(order); this._updateContent(); } } return false; }
    _handleDragEnd(e) { this.shadowRoot.querySelectorAll('.scene-btn').forEach(col => { col.classList.remove('over'); col.classList.remove('dragging'); }); }

    _toggleMenu(forceOpen = null) {
        this.isMenuOpen = forceOpen !== null ? forceOpen : !this.isMenuOpen;
        if (this.isMenuOpen) {
            this.creationArea.classList.add("open");
            this.content.classList.add("edit-mode");
            if (!this.editingId && this.mainLightsContainer.innerHTML === "") this._buildLightControls(null);
        }
        else {
            this.creationArea.classList.remove("open");
            this.content.classList.remove("edit-mode");
            this._stopEditing();
        }
        this._updateToggleIcon();
        this._updateContent();
    }

    _renderIconPicker() {
        this.iconList.innerHTML = "";
        PRESET_ICONS.forEach(icon => {
            const el = document.createElement("div"); el.className = "icon-option";
            if (icon === this.currentIcon) el.classList.add("selected");
            el.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`;
            el.addEventListener("click", () => {
                this.shadowRoot.querySelectorAll(".icon-option").forEach(i => i.classList.remove("selected"));
                el.classList.add("selected");
                this.currentIcon = icon;
            });
            this.iconList.appendChild(el);
        });
    }

    _saveScene() {
        const name = this.inputName.value; if (!name) return alert("Nom vide !");
        const room = this.currentRoom.toLowerCase(); if (!room) return alert("Aucune pièce");
        const color = this.inputColor.value; const iconToSave = this.currentIcon;
        const slug = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const shortId = `${room}_${slug}`; const newEntityId = `scene.${shortId}`;
        const checkboxes = this.shadowRoot.querySelectorAll(".light-select:checked");
        const selectedLights = Array.from(checkboxes).map(cb => cb.dataset.entity);
        if (selectedLights.length === 0) return alert(`Sélectionnez au moins une lumière !`);

        const meta = this._loadMeta();
        const snapshot = {}; selectedLights.forEach(eid => { snapshot[eid] = "included"; });
        meta[newEntityId] = { icon: iconToSave, color: color, snapshot: snapshot };
        this._saveMeta(meta);

        if (this.editingId && this.editingId !== newEntityId) {
            if (confirm("Renommer la scène ?")) {
                this._hass.callService("python_script", "delete_entity", { entity_id: this.editingId });
                delete meta[this.editingId]; this._saveMeta(meta);
                let order = this._loadOrder(); const idx = order.indexOf(this.editingId);
                if (idx !== -1) { order[idx] = newEntityId; this._saveOrder(order); }
            } else return;
        } else {
            if (!this.editingId) { const currentOrder = this._loadOrder(); if (!currentOrder.includes(newEntityId)) { currentOrder.push(newEntityId); this._saveOrder(currentOrder); } }
        }

        this._hass.callService("scene", "create", { scene_id: shortId, snapshot_entities: selectedLights });
        const updateState = () => { this._hass.callService("python_script", "set_state", { entity_id: newEntityId, icon: iconToSave, color: color }); };
        setTimeout(updateState, 500); setTimeout(updateState, 2000); setTimeout(updateState, 4000);
        this.inputName.value = ""; this._toggleMenu(false); this._updateContent();
    }

    _updateContent() {
        if (!this.currentRoom) return;
        const prefix = `scene.${this.currentRoom.toLowerCase()}_`;
        let scenes = Object.keys(this._hass.states).filter((eid) => eid.startsWith(prefix) && this._hass.states[eid].state !== 'unavailable');
        const storedOrder = this._loadOrder(); const meta = this._loadMeta();
        if (storedOrder.length > 0) { scenes.sort((a, b) => { const indexA = storedOrder.indexOf(a); const indexB = storedOrder.indexOf(b); return (indexA === -1 ? 9999 : indexA) - (indexB === -1 ? 9999 : indexB); }); }

        this.content.innerHTML = scenes.length === 0 ? `<div class="empty">Aucune scène</div>` : "";
        if (this.isMenuOpen) this.content.classList.add("edit-mode");
        const btnStyle = this.config.button_style || 'filled'; const btnShape = this.config.button_shape || 'rounded';

        scenes.forEach((entityId) => {
            let name = entityId.replace(prefix, "").replace(/_/g, " ");
            name = name.charAt(0).toUpperCase() + name.slice(1);
            const btn = document.createElement("div");
            btn.className = `scene-btn style-${btnStyle} shape-${btnShape}`;

            const localData = meta[entityId];
            const stateAttributes = this._hass.states[entityId].attributes;
            const themeColor = localData?.color || stateAttributes.theme_color || "var(--primary-text-color)";
            const icon = localData?.icon || stateAttributes.icon || "mdi:palette";

            btn.style.setProperty('--btn-icon-color', themeColor);
            btn.dataset.entityId = entityId;
            if (this.editingId === entityId) btn.classList.add("being-edited");

            btn.innerHTML = `<div class="action-badge edit-badge"><ha-icon icon="mdi:pencil" style="--mdc-icon-size: 14px;"></ha-icon></div><div class="action-badge delete-badge"><ha-icon icon="mdi:close" style="--mdc-icon-size: 14px;"></ha-icon></div><ha-icon icon="${icon}"></ha-icon><span>${name}</span>`;

            if (this.isMenuOpen) {
                btn.setAttribute('draggable', 'true'); btn.classList.add('draggable');
                btn.addEventListener('dragstart', this._handleDragStart.bind(this));
                btn.addEventListener('dragenter', this._handleDragOver.bind(this));
                btn.addEventListener('dragover', this._handleDragOver.bind(this));
                btn.addEventListener('dragleave', this._handleDragLeave.bind(this));
                btn.addEventListener('drop', this._handleDrop.bind(this));
                btn.addEventListener('dragend', this._handleDragEnd.bind(this));
            } else {
                btn.addEventListener("click", () => {
                    this._hass.callService("scene", "turn_on", { entity_id: entityId, transition: 2 });
                    btn.classList.add("activated"); setTimeout(() => btn.classList.remove("activated"), 1500);
                });
            }
            btn.querySelector(".delete-badge").addEventListener("click", (e) => {
                e.stopPropagation(); if (confirm(`Supprimer "${name}" ?`)) {
                    this._hass.callService("python_script", "delete_entity", { entity_id: entityId });
                    const m = this._loadMeta(); delete m[entityId]; this._saveMeta(m);
                    this.cachedOrder = this.cachedOrder.filter(id => id !== entityId); this._pushToServer();
                    btn.style.opacity = "0"; btn.style.width = "0px"; setTimeout(() => btn.remove(), 300);
                    if (this.editingId === entityId) this._stopEditing();
                }
            });
            btn.querySelector(".edit-badge").addEventListener("click", (e) => {
                e.stopPropagation();
                if (this.editingId === entityId) { this._stopEditing(); }
                else {
                    const sceneColor = this._hass.states[entityId].attributes.theme_color;
                    this._startEditing(entityId, name, icon, sceneColor);
                }
            });
            this.content.appendChild(btn);
        });
    }
    getCardSize() { return 3; }
}

class SceneManagerEditor extends HTMLElement {
    setConfig(config) { this._config = config; this.render(); }
    configChanged(newConfig) { const event = new Event("config-changed", { bubbles: true, composed: true }); event.detail = { config: newConfig }; this.dispatchEvent(event); }
    render() {
        if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
      <style>
        .card-config { display: flex; flex-direction: column; gap: 20px; padding: 10px; }
        .option-group { border: 1px solid var(--divider-color, #ccc); border-radius: 8px; padding: 16px; }
        h3 { margin-top: 0; margin-bottom: 16px; border-bottom: 1px solid var(--divider-color, #ccc); padding-bottom: 8px; color: var(--primary-text-color); }
        .row { display: flex; align-items: center; gap: 15px; margin-bottom: 12px; }
        .label { flex: 0 0 140px; font-weight: 500; color: var(--primary-text-color); }
        input, select { flex: 1; padding: 10px; border-radius: 4px; border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color); color: var(--primary-text-color); box-sizing: border-box; }
        ha-icon-picker { flex: 1; }
      </style>
      <div class="card-config">
        <div class="option-group">
            <h3>⚙️ Configuration</h3>
            <div class="row"><div class="label">Titre</div><input type="text" id="title" value="${this._config.title || ''}"></div>
            <div class="row"><div class="label">Icône Titre</div><ha-icon-picker id="icon" value="${this._config.icon || 'mdi:home-floor-1'}"></ha-icon-picker></div>
            <div class="row"><div class="label">Pièce Fixe</div><input type="text" id="room" value="${this._config.room || ''}" placeholder="Optionnel (ex: salon)"></div>
        </div>
        <div class="option-group">
            <h3>🎨 Apparence</h3>
            <div class="row"><div class="label">Style Bouton</div><select id="button_style"><option value="filled" ${this._config.button_style === 'filled' ? 'selected' : ''}>Plein (Filled)</option><option value="outline" ${this._config.button_style === 'outline' ? 'selected' : ''}>Contour (Outline)</option><option value="ghost" ${this._config.button_style === 'ghost' ? 'selected' : ''}>Transparent (Ghost)</option></select></div>
            <div class="row"><div class="label">Forme Bouton</div><select id="button_shape"><option value="rounded" ${this._config.button_shape === 'rounded' ? 'selected' : ''}>Arrondi</option><option value="box" ${this._config.button_shape === 'box' ? 'selected' : ''}>Carré</option><option value="circle" ${this._config.button_shape === 'circle' ? 'selected' : ''}>Rond</option></select></div>
            <div class="row"><div class="label">Alignement</div><select id="scene_alignment"><option value="left" ${this._config.scene_alignment === 'left' ? 'selected' : ''}>Gauche</option><option value="center" ${this._config.scene_alignment === 'center' ? 'selected' : ''}>Centre</option><option value="right" ${this._config.scene_alignment === 'right' ? 'selected' : ''}>Droite</option></select></div>
        </div>
        <div class="option-group">
            <h3>📐 Dimensions</h3>
            <div class="row"><div class="label">Largeur</div><input type="text" id="button_width" value="${this._config.button_width || '100px'}"></div>
            <div class="row"><div class="label">Hauteur</div><input type="text" id="button_height" value="${this._config.button_height || '80px'}"></div>
        </div>
      </div>
    `;
        this.shadowRoot.querySelectorAll("input, select").forEach(el => {
            el.addEventListener("change", (e) => {
                const newConfig = { ...this._config };
                newConfig[e.target.id] = e.target.value;
                this.configChanged(newConfig);
            });
        });

        const iconPicker = this.shadowRoot.getElementById("icon");
        if (iconPicker) {
            iconPicker.addEventListener("value-changed", (e) => {
                const newConfig = { ...this._config };
                newConfig.icon = e.detail.value;
                this.configChanged(newConfig);
            });
        }
    }
}

customElements.define("scene-manager-card", SceneManagerCard);
customElements.define("scene-manager-editor", SceneManagerEditor);