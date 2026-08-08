import streamlit as st
import time
import json
import zipfile
import io
import re
import os

# 1. Page Configuration
st.set_page_config(
    page_title="ProtoLens AI — IIUI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Session State Navigation Setup
if "page" not in st.session_state:
    st.session_state.page = "main"

if "audit_complete" not in st.session_state:
    st.session_state.audit_complete = False

if "last_file_hash" not in st.session_state:
    st.session_state.last_file_hash = None

if "dynamic_results" not in st.session_state:
    st.session_state.dynamic_results = None


# 3. Code Quality & Deficiency Analysis Engine
def analyze_codebase_zip(zip_bytes, target_domain: str, compliance_standard: str):
    """
    Parses uploaded ZIP archive for source code quality, architecture checks,
    and granular code deficiencies (secrets, error handling, debug statements, etc.).
    """
    
    files_found = []
    total_size = 0
    file_contents = {}

    lang_map = {
        'py': 'Python', 'js': 'JavaScript', 'ts': 'TypeScript', 'jsx': 'React JS',
        'tsx': 'React TS', 'cpp': 'C++', 'c': 'C', 'h': 'C/C++ Header',
        'java': 'Java', 'cs': 'C#', 'php': 'PHP', 'rb': 'Ruby', 'go': 'Go',
        'rs': 'Rust', 'html': 'HTML', 'css': 'CSS', 'sql': 'SQL', 'sh': 'Shell'
    }

    detected_languages = set()
    has_readme = False
    has_dependencies = False
    has_tests = False
    has_config = False
    has_gitignore = False

    issues = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            if not info.is_dir():
                filename = os.path.basename(info.filename)
                files_found.append(info.filename)
                total_size += info.file_size
                
                ext = info.filename.split('.')[-1].lower() if '.' in info.filename else ''
                if ext in lang_map:
                    detected_languages.add(lang_map[ext])

                filename_lower = filename.lower()
                if 'readme' in filename_lower:
                    has_readme = True
                if filename_lower in ['requirements.txt', 'package.json', 'pyproject.toml', 'cargo.toml', 'build.gradle', 'pom.xml', 'go.mod', 'cmakelists.txt', 'setup.py']:
                    has_dependencies = True
                if 'test' in filename_lower or info.filename.startswith('tests/'):
                    has_tests = True
                if filename_lower in ['.env.example', 'dockerfile', 'docker-compose.yml', 'config.json', 'settings.py']:
                    has_config = True
                if '.gitignore' in filename_lower:
                    has_gitignore = True

                # Code file content analysis
                if ext in ['py', 'js', 'ts', 'jsx', 'tsx', 'html', 'css', 'cpp', 'c', 'java', 'php', 'go', 'json']:
                    try:
                        content = z.read(info.filename).decode('utf-8', errors='ignore')
                        file_contents[info.filename] = content
                    except Exception:
                        pass

    # --- CODE-LEVEL DEFICIENCY CHECKS ---
    secrets_count = 0
    print_debug_count = 0
    bare_except_count = 0
    oversized_files = []

    for filepath, content in file_contents.items():
        lines = content.splitlines()

        # Check 1: Large file size (Deficiency)
        if len(lines) > 300:
            oversized_files.append((filepath, len(lines)))

        # Check 2: Hardcoded Secrets (Critical Deficiency)
        if re.search(r'(api_key|secret_key|password|bearer|auth_token)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', content, re.IGNORECASE):
            secrets_count += 1
            issues.append({
                "category": "Security Defect",
                "severity": "CRITICAL",
                "title": f"Hardcoded Secrets in `{os.path.basename(filepath)}`",
                "agent": "Reasoning Agent",
                "badge": "badge-critical",
                "class": "issue-card-critical",
                "desc": f"Potential API keys, credentials, or tokens hardcoded in `{filepath}`. Move credentials to an environment file (.env)."
            })

        # Check 3: Bare Exceptions / Poor Error Handling
        if re.search(r'except\s*:', content) or re.search(r'catch\s*\(\s*e\s*\)\s*\{\s*\}', content):
            bare_except_count += 1
            issues.append({
                "category": "Code Quality Defect",
                "severity": "WARNING",
                "title": f"Weak Error Handling in `{os.path.basename(filepath)}`",
                "agent": "UX Agent",
                "badge": "badge-warning",
                "class": "issue-card-warning",
                "desc": f"Found bare `except:` or empty catch block in `{filepath}`. Suppressing errors leads to silent execution failures."
            })

        # Check 4: Leftover Debugging Statements
        debug_matches = len(re.findall(r'print\(|console\.log\(', content))
        if debug_matches > 3:
            print_debug_count += debug_matches
            issues.append({
                "category": "Code Hygiene",
                "severity": "WARNING",
                "title": f"Excessive Debug Logging in `{os.path.basename(filepath)}`",
                "agent": "UI Agent",
                "badge": "badge-warning",
                "class": "issue-card-warning",
                "desc": f"Identified {debug_matches} unhandled `print()` or `console.log()` statements in `{filepath}`. Replace with standard logging framework."
            })

    # --- ARCHITECTURE DEFICIENCY CHECKS ---
    if not has_readme:
        issues.append({
            "category": "Documentation Defect",
            "severity": "CRITICAL",
            "title": "Missing Documentation (README)",
            "agent": "Product Agent",
            "badge": "badge-critical",
            "class": "issue-card-critical",
            "desc": "No README found. Project lacks setup instructions, usage guidelines, or software overview."
        })

    if not has_dependencies:
        issues.append({
            "category": "Build Defect",
            "severity": "CRITICAL",
            "title": "Missing Package Dependency Manifest",
            "agent": "Architecture Agent",
            "badge": "badge-critical",
            "class": "issue-card-critical",
            "desc": "Missing `requirements.txt`, `package.json`, or equivalent manifest. Third-party packages cannot be restored."
        })

    if not has_tests:
        issues.append({
            "category": "Testing Defect",
            "severity": "WARNING",
            "title": "No Automated Unit Tests Identified",
            "agent": "Accessibility Agent",
            "badge": "badge-warning",
            "class": "issue-card-warning",
            "desc": "No test directory or test suites detected. Software changes cannot be validated automatically."
        })

    if oversized_files:
        for fname, lcount in oversized_files[:2]:
            issues.append({
                "category": "Maintainability Defect",
                "severity": "WARNING",
                "title": f"Oversized File (`{os.path.basename(fname)}`)",
                "agent": "Architecture Agent",
                "badge": "badge-warning",
                "class": "issue-card-warning",
                "desc": f"`{fname}` spans {lcount} lines. High complexity file; refactor into smaller modular helper scripts."
            })

    # Scoring & Metrics Calculation
    critical_defects = sum(1 for i in issues if i["severity"] == "CRITICAL")
    warning_defects = sum(1 for i in issues if i["severity"] == "WARNING")
    
    deductions = (critical_defects * 15) + (warning_defects * 5)
    overall_score = max(20, min(98, 100 - deductions))
    architecture_rating = "High Quality" if overall_score >= 80 else "Needs Improvement" if overall_score >= 50 else "Critical Deficiencies"
    primary_languages = ", ".join(list(detected_languages)[:4]) if detected_languages else "Generic Code"

    return {
        "file_count": len(files_found),
        "total_size_kb": f"{round(total_size / 1024, 1)} KB",
        "primary_languages": primary_languages,
        "overall_score": overall_score,
        "architecture_rating": architecture_rating,
        "critical_count": critical_defects,
        "warning_count": warning_defects,
        "total_issues_count": len(issues),
        "issues": issues,
        "file_list": files_found[:15]
    }


# 4. Custom CSS
hide_sidebar_css = ""
if st.session_state.page == "main":
    hide_sidebar_css = """
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    """

st.markdown(f"""
<style>
    {hide_sidebar_css}

    .stApp {{
        background-color: #0A192F;
        color: #F8FAFC;
    }}

    [data-testid="stSidebar"] {{
        background-color: #0F172A !important;
        border-right: 1px solid #1E3A8A;
    }}

    .navy-card {{
        background-color: #1E293B;
        border: 1px solid #1E3A8A;
        border-radius: 14px;
        padding: 2.2rem;
        box-shadow: 0 10px 25px -5px rgba(2, 6, 23, 0.6);
        margin-bottom: 1.5rem;
    }}

    .hero-navy {{
        background: linear-gradient(135deg, #0A192F 0%, #172554 50%, #1E3A8A 100%);
        border: 1px solid #2563EB;
        border-radius: 16px;
        padding: 2.5rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 12px 30px -5px rgba(2, 6, 23, 0.8);
    }}

    .hero-title {{
        font-size: 2.8rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }}

    .hero-subtitle {{
        font-size: 1.15rem;
        color: #93C5FD;
        margin-bottom: 0;
    }}

    .team-card {{
        background: #0F172A;
        border: 1px solid #1E3A8A;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }}

    .team-name {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #E0F2FE;
    }}

    .team-role {{
        font-size: 0.88rem;
        color: #93C5FD;
    }}

    .team-reg {{
        font-size: 0.8rem;
        color: #60A5FA;
        font-weight: 600;
    }}

    .issue-card {{
        background-color: #0F172A;
        border: 1px solid #1E3A8A;
        border-left: 5px solid #2563EB;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }}
    .issue-card-critical {{
        border-left-color: #EF4444;
    }}
    .issue-card-warning {{
        border-left-color: #F59E0B;
    }}

    .badge {{
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }}
    .badge-critical {{
        background-color: rgba(239, 68, 68, 0.2);
        color: #FCA5A5;
        border: 1px solid #EF4444;
    }}
    .badge-warning {{
        background-color: rgba(245, 158, 11, 0.2);
        color: #FDE68A;
        border: 1px solid #F59E0B;
    }}

    div[data-testid="stFileUploader"] {{
        background-color: #0F172A;
        border: 2px dashed #1E3A8A;
        border-radius: 12px;
        padding: 1rem;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 48px;
        background-color: #0F172A;
        border-radius: 8px;
        color: #93C5FD;
        border: 1px solid #1E3A8A;
        padding: 0 16px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
        border-color: #3B82F6 !important;
    }}
</style>
""", unsafe_allow_html=True)


# ==========================================
# PAGE 1: MAIN PAGE (NO SIDEBAR)
# ==========================================
if st.session_state.page == "main":
    
    st.markdown("""
    <div class="hero-navy">
        <div style="color: #60A5FA; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.85rem; margin-bottom: 0.5rem;">
            International Islamic University Islamabad
        </div>
        <div class="hero-title">ProtoLens AI</div>
        <div class="hero-subtitle">B.E Tech(AI)</div>
    </div>
    """, unsafe_allow_html=True)

    col_info, col_team = st.columns([1, 1], gap="large")

    with col_info:
        st.markdown("""
        <div class="navy-card">
            <h3 style="color: #60A5FA; margin-top: 0;">🏛️ Academic Details</h3>
            <p><strong>Institution:</strong> International Islamic University Islamabad (IIUI)</p>
            <p><strong>Program:</strong> B.E Tech(AI)</p>
            <p><strong>Department:</strong> Department of Electrical & Computer Engineering</p>
            <p><strong>Official Contact Email:</strong> <br><code style="color: #93C5FD;">tehreenramesha2102005@gmail.com</code></p>
            <hr style="border-color: #1E3A8A; margin: 1.5rem 0;">
            <p style="color: #94A3B8; font-size: 0.95rem;">
                This system provides automated agentic inspection, code deficiency auditing, vulnerability checks, and architecture scoring for any codebase.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_team:
        st.markdown("""
        <div class="navy-card">
            <h3 style="color: #60A5FA; margin-top: 0;">👥 Project Team</h3>
            <div class="team-card">
                <div class="team-name">Tehreen Ramesha</div>
                <div class="team-role">Team Leader</div>
                <div class="team-reg">Registration No: 012218</div>
            </div>
            <div class="team-card">
                <div class="team-name">Amna Mudassar Ali</div>
                <div class="team-role">Technical Supervisor</div>
                <div class="team-reg">Registration No: 016809</div>
            </div>
            <div class="team-card">
                <div class="team-name">Ayesha Bint e Israr</div>
                <div class="team-role">Developer</div>
                <div class="team-reg">Registration No: 012214</div>
            </div>
            <div class="team-card">
                <div class="team-name">Fatima Arshad</div>
                <div class="team-role">Student Researcher</div>
                <div class="team-reg">Registration No: 012221</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("🚀 Welcome to Dashboard ➔", type="primary", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()


# ==========================================
# PAGE 2: DASHBOARD PAGE (WITH SIDEBAR)
# ==========================================
elif st.session_state.page == "dashboard":

    with st.sidebar:
        st.markdown('<h2 style="color:#FFFFFF; margin-bottom:0;">⚡ Dashboard</h2>', unsafe_allow_html=True)
        st.caption("AI Code Deficiency Audit Studio")
        st.divider()

        if st.button("⬅️ Back to Main Page", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()

        st.divider()
        st.markdown("### 🤖 Active Agent Team")
        agents_list = [
            ("👁️ Vision Agent", "File Hierarchy & Archive Inspector"),
            ("📝 OCR Agent", "Source Code Content Parser"),
            ("🎨 UI Agent", "Code Hygiene & Style Inspector"),
            ("🧠 UX Agent", "Error Handling & Logic Auditor"),
            ("♿ Accessibility Agent", "Security & Secret Scanner"),
            ("📋 Product Agent", "Manifest & Documentation Inspector"),
            ("⚖️ Reasoning Agent", "Risk & Deficiency Evaluator"),
            ("📄 Report Agent", "Deficiency JSON Synthesis")
        ]
        for name, role in agents_list:
            st.markdown(f"""
            <div style="background:#0A192F; border:1px solid #1E3A8A; border-radius:6px; padding:0.5rem 0.8rem; margin-bottom:0.4rem; font-size:0.85rem;">
                <strong style="color:#E0F2FE;">{name}</strong><br>
                <span style="color:#60A5FA;">{role}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.caption("          IIUI B.E Tech(AI)          ")

    st.markdown("""
    <div style="background:#1E293B; border:1px solid #1E3A8A; border-radius:12px; padding:1.5rem 2rem; margin-bottom:1.8rem;">
        <h2 style="color:#FFFFFF; margin:0;">📊 Dynamic Code Deficiency Inspection Studio</h2>
        <p style="color:#93C5FD; margin:0.3rem 0 0 0;">Upload any software project source code (.ZIP archive) to execute deep static code analysis and identify critical deficiencies.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Source Code Archive (.ZIP)",
        type=["zip"]
    )

    if uploaded_file is not None:
        current_hash = hash(uploaded_file.name + str(uploaded_file.size))
        if st.session_state.last_file_hash != current_hash:
            st.session_state.last_file_hash = current_hash
            st.session_state.audit_complete = False
            st.session_state.dynamic_results = None

        col_img, col_ctrl = st.columns([1, 1], gap="large")

        with col_img:
            st.markdown("### 📦 Uploaded Code Archive")
            st.info(f"**File:** {uploaded_file.name}\n\n**Size:** {round(uploaded_file.size / 1024, 2)} KB")

        with col_ctrl:
            st.markdown("### ⚙️ Audit Configuration")
            target_domain = st.selectbox(
                "Project Context",
                ["Web Application", "Machine Learning / AI", "Mobile Application", "API / Backend Service", "Desktop Application", "Embedded / C++ Code"]
            )
            compliance_standard = st.selectbox(
                "Deficiency Review Standard",
                ["Strict Code Quality Standard", "Production Readiness Standard", "Basic Student Prototype Standard"]
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 Run Code Deficiency Audit", type="primary", use_container_width=True):
                st.divider()
                progress_bar = st.progress(0)
                status_text = st.empty()

                agents_flow = [
                    ("👁️ Vision Agent", "Extracting archive hierarchy...", 0.15),
                    ("📝 OCR Agent", "Reading source code contents...", 0.30),
                    ("🎨 UI Agent", "Checking debug statements & formatting...", 0.45),
                    ("🧠 UX Agent", "Inspecting error handling and try/catch blocks...", 0.60),
                    ("♿ Accessibility Agent", "Scanning for hardcoded API keys & secrets...", 0.75),
                    ("📋 Product Agent", "Checking README and dependency manifests...", 0.85),
                    ("⚖️ Reasoning Agent", "Calculating deficiency scores and deductions...", 0.95),
                    ("📄 Report Agent", "Generating deficiency JSON report...", 1.00),
                ]

                for agent_name, desc, step_pct in agents_flow:
                    status_text.markdown(f"**{agent_name}:** {desc}")
                    progress_bar.progress(step_pct)
                    time.sleep(0.3)

                zip_bytes = uploaded_file.getvalue()
                st.session_state.dynamic_results = analyze_codebase_zip(zip_bytes, target_domain, compliance_standard)
                status_text.success("✅ Code Deficiency Audit Completed!")
                st.session_state.audit_complete = True

        if st.session_state.audit_complete and st.session_state.dynamic_results:
            results = st.session_state.dynamic_results
            st.divider()
            st.markdown(f"## 📈 Deficiency Findings & Metrics for `{uploaded_file.name}`")

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric(label="Quality Score", value=f"{results['overall_score']}/100")
            with m2:
                st.metric(label="Status", value=results['architecture_rating'])
            with m3:
                st.metric(label="Deficiencies Found", value=results['total_issues_count'], delta=f"-{results['critical_count']} Critical", delta_color="inverse")
            with m4:
                st.metric(label="Files Scanned", value=results['file_count'])

            tabs = st.tabs([
                "🚨 Identified Deficiencies", 
                "📌 Executive Summary", 
                "📂 Analyzed File Tree", 
                "📄 Download Audit JSON"
            ])

            with tabs[0]:
                st.markdown("### Detected Code & Architecture Deficiencies")
                if results['issues']:
                    for issue in results['issues']:
                        st.markdown(f"""
                        <div class="issue-card {issue['class']}">
                            <span class="badge {issue['badge']}">{issue['severity']}</span> <strong>{issue['title']}</strong><br>
                            <em>Assigned Agent: {issue['agent']}</em><br>
                            <span style="color:#CBD5E1;">{issue['desc']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("🎉 No major code or architecture deficiencies detected in the uploaded project!")

            with tabs[1]:
                st.markdown("### Executive Summary")
                st.write(f"""
                - **Project:** `{uploaded_file.name}` ({results['total_size_kb']})
                - **Languages Detected:** {results['primary_languages']}
                - **Critical Vulnerabilities / Missing Manifests:** {results['critical_count']}
                - **Code Hygiene & Quality Warnings:** {results['warning_count']}
                - **Overall Code Base Score:** {results['overall_score']}/100
                """)

            with tabs[2]:
                st.markdown("### File Structure")
                for f in results['file_list']:
                    st.code(f, language="text")

            with tabs[3]:
                st.markdown("### Export Report")
                report_data = {
                    "project_name": "ProtoLens AI",
                    "file_analyzed": uploaded_file.name,
                    "target_domain": target_domain,
                    "languages_detected": results['primary_languages'],
                    "file_count": results['file_count'],
                    "overall_score": results['overall_score'],
                    "status": results['architecture_rating'],
                    "total_deficiencies": results['total_issues_count'],
                    "critical_deficiencies": results['critical_count'],
                    "warning_deficiencies": results['warning_count'],
                    "deficiency_details": results['issues']
                }
                st.download_button(
                    label="📥 Download Deficiency Report (JSON)",
                    data=json.dumps(report_data, indent=2),
                    file_name=f"{uploaded_file.name}_deficiency_report.json",
                    mime="application/json",
                    use_container_width=True
                )
    else:
        st.info("👈 Please upload a ZIP project archive above to run the code deficiency audit.")
