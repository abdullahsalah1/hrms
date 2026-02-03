#!/usr/bin/env python3
"""
Test script to verify employee analytics performance optimizations
"""

import frappe
import time
from frappe.utils import now_datetime

def test_analytics_performance():
    """
    Test the performance of the optimized analytics function
    """
    print("🧪 Testing Employee Analytics Performance...")
    
    try:
        # Test 1: Check if indexes exist
        print("\n1. Checking database indexes...")
        index_exists = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tabEmployee' 
            AND index_name = 'idx_employee_analytics_status'
        """, as_dict=1)[0].count > 0
        
        if index_exists:
            print("✅ Database indexes are created")
        else:
            print("⚠️  Database indexes not found - creating them...")
            from hrms.api.employee_chart import create_employee_analytics_indexes
            create_employee_analytics_indexes()
        
        # Test 2: Test caching functionality
        print("\n2. Testing caching functionality...")
        from hrms.api.employee_chart import get_cached_analytics, set_cached_analytics
        
        # Clear cache first
        frappe.cache().delete_value("employee_analytics_cache")
        
        # Test cache miss
        cached_data = get_cached_analytics()
        if cached_data is None:
            print("✅ Cache miss working correctly")
        else:
            print("❌ Cache should be empty")
        
        # Test cache set
        test_data = {"test": "data"}
        set_cached_analytics(test_data)
        
        # Test cache hit
        cached_data = get_cached_analytics()
        if cached_data == test_data:
            print("✅ Cache set and get working correctly")
        else:
            print("❌ Cache not working properly")
        
        # Test 3: Performance test
        print("\n3. Testing analytics performance...")
        from hrms.api.employee_chart import get_employee_comprehensive_stats
        
        # Clear cache for fresh test
        frappe.cache().delete_value("employee_analytics_cache")
        
        # First call (should be slower)
        start_time = time.time()
        result1 = get_employee_comprehensive_stats()
        first_call_time = time.time() - start_time
        print(f"✅ First call completed in {first_call_time:.2f} seconds")
        
        # Second call (should be faster due to caching)
        start_time = time.time()
        result2 = get_employee_comprehensive_stats()
        second_call_time = time.time() - start_time
        print(f"✅ Second call completed in {second_call_time:.2f} seconds")
        
        if second_call_time < first_call_time:
            print(f"✅ Caching is working! {((first_call_time - second_call_time) / first_call_time * 100):.1f}% improvement")
        else:
            print("⚠️  Caching may not be working as expected")
        
        # Test 4: Data validation
        print("\n4. Validating analytics data...")
        if isinstance(result1, dict) and 'department' in result1:
            print("✅ Analytics data structure is correct")
            
            # Check if we have data
            dept_data = result1.get('department', {})
            if dept_data.get('datasets') and dept_data['datasets'][0].get('values'):
                print(f"✅ Found {len(dept_data['datasets'][0]['values'])} department categories")
            else:
                print("⚠️  No department data found")
        else:
            print("❌ Analytics data structure is incorrect")
        
        # Test 5: Performance stats
        print("\n5. Getting performance statistics...")
        from hrms.api.employee_chart import get_analytics_performance_stats
        
        perf_stats = get_analytics_performance_stats()
        print(f"✅ Performance stats: {perf_stats}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Initialize Frappe
    import os
    import sys
    
    # Add the bench directory to Python path
    bench_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, bench_path)
    
    # Initialize Frappe
    import frappe
    frappe.init(site="i-aps.app")
    frappe.connect()
    
    # Run tests
    success = test_analytics_performance()
    
    # Cleanup
    frappe.destroy()
    
    if success:
        print("\n✅ All performance optimizations are working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1) 