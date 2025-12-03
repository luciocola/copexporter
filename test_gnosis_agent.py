"""
Test script for GNOSIS DGGS Agent
Can be run standalone or from QGIS Python console
"""
import sys
import os

# Add plugin path if running from QGIS
plugin_path = os.path.dirname(__file__)
if plugin_path not in sys.path:
    sys.path.append(plugin_path)

try:
    from qgis.core import QgsRectangle
    from gnosis_dggs_agent import GnosisDGGSAgent
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    print("QGIS not available - running in limited mode")


def test_basic_query():
    """Test basic GNOSIS Earth API query"""
    if not QGIS_AVAILABLE:
        print("Skipping test - QGIS not available")
        return False
    
    print("\n=== Testing GNOSIS DGGS Agent ===\n")
    
    agent = GnosisDGGSAgent()
    
    # Test extent (San Francisco Bay Area)
    extent = QgsRectangle(-122.5, 37.7, -122.3, 37.9)
    
    print(f"Query extent: {extent.toString()}")
    print(f"DGGS CRS: rHEALPix-R12\n")
    
    # Get coverage summary
    print("Querying GNOSIS Earth API...")
    summary = agent.get_coverage_summary(extent, "rHEALPix-R12")
    
    if summary['success']:
        print("\n✓ Query successful!")
        print(f"  DGGS Zones: {summary['zone_count']}")
        print(f"  Features: {summary['feature_count']}")
        
        if summary.get('zones'):
            print(f"  Zone IDs: {', '.join(summary['zones'][:5])}")
            if len(summary['zones']) > 5:
                print(f"           ... (+{len(summary['zones']) - 5} more)")
        
        if 'elevation_stats' in summary:
            elev = summary['elevation_stats']
            print(f"  Elevation Range: {elev['min']}m to {elev['max']}m")
        
        return True
    else:
        print(f"\n✗ Query failed: {summary['error']}")
        return False


def test_zone_listing():
    """Test getting list of DGGS zones"""
    if not QGIS_AVAILABLE:
        print("Skipping test - QGIS not available")
        return False
    
    print("\n=== Testing Zone Listing ===\n")
    
    agent = GnosisDGGSAgent()
    extent = QgsRectangle(-122.5, 37.7, -122.3, 37.9)
    
    print("Getting DGGS zones...")
    zones = agent.get_dggs_zones_for_extent(extent, "rHEALPix-R12")
    
    if zones:
        print(f"\n✓ Found {len(zones)} zones:")
        for zone in zones[:10]:
            print(f"  - {zone}")
        if len(zones) > 10:
            print(f"  ... (+{len(zones) - 10} more)")
        return True
    else:
        print("\n✗ No zones found")
        return False


def test_url_construction():
    """Test URL building"""
    if not QGIS_AVAILABLE:
        print("Skipping test - QGIS not available")
        return False
    
    print("\n=== Testing URL Construction ===\n")
    
    agent = GnosisDGGSAgent()
    extent = QgsRectangle(-122.5, 37.7, -122.3, 37.9)
    
    url = agent.build_query_url(extent, "rHEALPix-R12", zone_id="R05_08")
    
    print(f"Constructed URL:")
    print(f"{url}\n")
    
    # Verify URL components
    assert "bbox=" in url
    assert "dggs-crs=rHEALPix-R12" in url
    assert "zone-id=R05_08" in url
    assert "f=json" in url
    
    print("✓ URL construction correct")
    return True


def test_available_crs():
    """Test available DGGS CRS list"""
    print("\n=== Available DGGS CRS ===\n")
    
    agent = GnosisDGGSAgent()
    crs_list = agent.get_available_dggs_crs_list()
    
    print("Supported DGGS CRS:")
    for crs in crs_list:
        print(f"  - {crs}")
    
    print(f"\n✓ {len(crs_list)} DGGS CRS available")
    return True


def run_all_tests():
    """Run all tests"""
    print("╔═══════════════════════════════════════════╗")
    print("║  GNOSIS DGGS Agent Test Suite            ║")
    print("╚═══════════════════════════════════════════╝")
    
    if not QGIS_AVAILABLE:
        print("\n⚠ Warning: QGIS not available")
        print("Some tests will be skipped\n")
    
    results = []
    
    # Run tests
    results.append(("URL Construction", test_url_construction()))
    results.append(("Available CRS", test_available_crs()))
    results.append(("Basic Query", test_basic_query()))
    results.append(("Zone Listing", test_zone_listing()))
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary:")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*50)
    print(f"Total: {passed}/{total} tests passed")
    print("="*50)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
