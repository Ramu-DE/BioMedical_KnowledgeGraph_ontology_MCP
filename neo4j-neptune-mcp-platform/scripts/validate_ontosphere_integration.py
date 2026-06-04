"""Validation script for Ontosphere integration.

Checks for:
1. Import dependencies
2. Missing API keys/config
3. Runtime compatibility
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_imports():
    """Check if all required imports are available."""
    issues = []
    
    # Core dependencies
    try:
        import rdflib
        print(f"✓ rdflib {rdflib.__version__}")
    except ImportError:
        issues.append("✗ rdflib not installed (pip install rdflib>=7.0.0)")
    
    try:
        import playwright
        print(f"✓ playwright {playwright.__version__}")
    except ImportError:
        issues.append("✗ playwright not installed (pip install playwright>=1.40.0)")
    
    try:
        from mcp.server import Server
        print("✓ mcp installed")
    except ImportError:
        issues.append("✗ mcp not installed (pip install mcp)")
    
    try:
        import pydantic
        print(f"✓ pydantic {pydantic.__version__}")
    except ImportError:
        issues.append("✗ pydantic not installed (pip install pydantic>=2.0.0)")
    
    return issues


def check_module_imports():
    """Check if our modules can be imported."""
    issues = []
    
    # Test imports without initializing (avoid needing API keys)
    modules = [
        "biomedical_kg_mcp.services.ontosphere_client",
        "biomedical_kg_mcp.services.ontology_module_loader",
        "biomedical_kg_mcp.services.ontosphere_config_generator",
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            issues.append(f"✗ {module}: {e}")
        except Exception as e:
            # Runtime errors are OK at this stage
            print(f"⚠ {module}: {type(e).__name__} (will need config)")
    
    return issues


def check_ontosphere_bridge():
    """Check OntosphereBridge can be instantiated (without API calls)."""
    try:
        from biomedical_kg_mcp.mcp_servers.ontosphere_bridge import OntosphereBridge
        
        # Check class structure
        bridge = OntosphereBridge.__new__(OntosphereBridge)
        
        # Verify methods exist
        methods = ['_load_module', '_validate', '_export_rdf', '_sync_to_neptune']
        missing = [m for m in methods if not hasattr(bridge, m)]
        
        if missing:
            return [f"✗ OntosphereBridge missing methods: {missing}"]
        
        print("✓ OntosphereBridge class structure valid")
        return []
        
    except Exception as e:
        return [f"✗ OntosphereBridge: {e}"]


def check_config_generator():
    """Test OntosphereConfigGenerator."""
    try:
        from biomedical_kg_mcp.services.ontosphere_config_generator import OntosphereConfigGenerator
        
        generator = OntosphereConfigGenerator()
        
        # Test URL generation
        url = generator.generate_url(persona="knowledge_engineer")
        
        if "thhanke.github.io/ontosphere" not in url:
            return [f"✗ Generated URL invalid: {url}"]
        
        if "ontology=" not in url:
            return [f"✗ Generated URL missing ontology param: {url}"]
        
        print(f"✓ OntosphereConfigGenerator: {url[:80]}...")
        return []
        
    except Exception as e:
        return [f"✗ OntosphereConfigGenerator: {e}"]


def check_ontology_loader():
    """Test OntologyModuleLoader."""
    try:
        from biomedical_kg_mcp.services.ontology_module_loader import OntologyModuleLoader
        
        loader = OntologyModuleLoader()
        
        # Check modules defined
        expected_modules = [
            "foundation", "commercial", "clinical", 
            "medical_affairs", "patient", "supply_quality", "governance"
        ]
        
        missing = [m for m in expected_modules if m not in loader.MODULES]
        if missing:
            return [f"✗ OntologyModuleLoader missing modules: {missing}"]
        
        # Test module info
        info = loader.get_module_info("foundation")
        if "uri" not in info or "classes" not in info:
            return ["✗ OntologyModuleLoader.get_module_info() incomplete"]
        
        print(f"✓ OntologyModuleLoader: {len(loader.MODULES)} modules defined")
        return []
        
    except Exception as e:
        return [f"✗ OntologyModuleLoader: {e}"]


def check_platform_integration():
    """Check platform.py integration."""
    try:
        with open("src/biomedical_kg_mcp/platform.py", "r") as f:
            content = f.read()
        
        checks = [
            ("ontosphere_bridge import", "from biomedical_kg_mcp.mcp_servers.ontosphere_bridge import OntosphereBridge"),
            ("ontosphere_bridge init", "self.ontosphere_bridge = OntosphereBridge"),
            ("ontosphere routing", 'elif method.startswith("ontosphere_")'),
            ("ontosphere cleanup", "await self.ontosphere_bridge.client.close()")
        ]
        
        issues = []
        for name, expected in checks:
            if expected in content:
                print(f"✓ platform.py: {name}")
            else:
                issues.append(f"✗ platform.py missing: {name}")
        
        return issues
        
    except Exception as e:
        return [f"✗ platform.py check failed: {e}"]


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Ontosphere Integration Validation")
    print("=" * 60)
    
    all_issues = []
    
    print("\n1. Checking dependencies...")
    all_issues.extend(check_imports())
    
    print("\n2. Checking module imports...")
    all_issues.extend(check_module_imports())
    
    print("\n3. Checking OntosphereBridge...")
    all_issues.extend(check_ontosphere_bridge())
    
    print("\n4. Checking OntosphereConfigGenerator...")
    all_issues.extend(check_config_generator())
    
    print("\n5. Checking OntologyModuleLoader...")
    all_issues.extend(check_ontology_loader())
    
    print("\n6. Checking platform.py integration...")
    all_issues.extend(check_platform_integration())
    
    print("\n" + "=" * 60)
    
    if all_issues:
        print("ISSUES FOUND:")
        for issue in all_issues:
            print(f"  {issue}")
        print("\n❌ Validation FAILED")
        return 1
    else:
        print("✅ All checks passed!")
        print("\nNext steps:")
        print("1. Install Playwright browsers: playwright install chromium")
        print("2. Set API keys in .env file")
        print("3. Test with: python -m src.biomedical_kg_mcp.services.ontosphere_config_generator")
        return 0


if __name__ == "__main__":
    sys.exit(main())
