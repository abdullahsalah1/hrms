import os

dashboard_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Employee Dashboard</title>
    
    <!-- Frappe Framework -->
    <script src="/assets/frappe/js/lib/jquery/jquery.min.js"></script>
    <script src="/assets/frappe/js/frappe/class.js"></script>
    <script src="/assets/frappe/js/frappe/form/formatters.js"></script>
    <script src="/assets/frappe/js/frappe/ui/messages.js"></script>
    <script src="/assets/frappe/js/frappe/request.js"></script>
    
    <!-- Dashboard Dependencies -->
    <link href="vendor/jquery-nice-select/css/nice-select.css" rel="stylesheet">
    <link rel="stylesheet" href="vendor/nouislider/nouislider.min.css">
    <link href="css/style.css" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <!-- Preloader -->
    <div id="preloader">
        <div class="waviy">
            <span style="--i:1">L</span>
            <span style="--i:2">o</span>
            <span style="--i:3">a</span>
            <span style="--i:4">d</span>
            <span style="--i:5">i</span>
            <span style="--i:6">n</span>
            <span style="--i:7">g</span>
            <span style="--i:8">.</span>
            <span style="--i:9">.</span>
            <span style="--i:10">.</span>
        </div>
    </div>

    <div id="main-wrapper">
        <!-- Nav Header -->
        <div class="nav-header">
            <a href="/" class="brand-logo">
                <svg class="logo-abbr" width="53" height="53" viewBox="0 0 53 53">
                    <path class="svg-logo-primary-path" d="M48.3418 41.8457H41.0957C36.8148 41.8457 33.332 38.3629 33.332 34.082C33.332 29.8011 36.8148 26.3184 41.0957 26.3184H48.3418V19.2275C48.3418 16.9408 46.4879 15.0869 44.2012 15.0869H4.14062C1.85386 15.0869 0 16.9408 0 19.2275V48.8594C0 51.1462 1.85386 53 4.14062 53H44.2012C46.4879 53 48.3418 51.1462 48.3418 48.8594V41.8457Z" fill="#5BCFC5"/>
                    <path class="svg-logo-primary-path" d="M51.4473 29.4238H41.0957C38.5272 29.4238 36.4375 31.5135 36.4375 34.082C36.4375 36.6506 38.5272 38.7402 41.0957 38.7402H51.4473C52.3034 38.7402 53 38.0437 53 37.1875V30.9766C53 30.1204 52.3034 29.4238 51.4473 29.4238ZM41.0957 35.6348C40.2382 35.6348 39.543 34.9396 39.543 34.082C39.543 33.2245 40.2382 32.5293 41.0957 32.5293C41.9532 32.5293 42.6484 33.2245 42.6484 34.082C42.6484 34.9396 41.9532 35.6348 41.0957 35.6348Z" fill="#5BCFC5"/>
                </svg>
                <p class="brand-title" style="font-size: 30px;">HRMS</p>
            </a>
            <div class="nav-control">
                <div class="hamburger">
                    <span class="line"></span><span class="line"></span><span class="line"></span>
                </div>
            </div>
        </div>

        <!-- Header -->
        <div class="header">
            <div class="header-content">
                <nav class="navbar navbar-expand">
                    <div class="collapse navbar-collapse justify-content-between">
                        <div class="header-left">
                            <div class="dashboard_bar">
                                Employee Dashboard
                            </div>
                        </div>
                        <ul class="navbar-nav header-right">
                            <li class="nav-item">
                                <div class="input-group search-area">
                                    <input type="text" class="form-control" placeholder="Search employees...">
                                    <span class="input-group-text"><a href="javascript:void(0)"><i class="flaticon-381-search-2"></i></a></span>
                                </div>
                            </li>
                            <li class="nav-item">
                                <a href="/desk" class="btn btn-primary d-sm-inline-block d-none">Back to Desk</a>
                            </li>
                        </ul>
                    </div>
                </nav>
            </div>
        </div>

        <!-- Sidebar -->
        <div class="dlabnav">
            <div class="dlabnav-scroll">
                <ul class="metismenu" id="menu">
                    <li class="dropdown header-profile">
                        <a class="nav-link" href="javascript:void(0);" role="button" data-bs-toggle="dropdown">
                            <img src="images/ion/man (1).png" width="20" alt=""/>
                            <div class="header-info ms-3">
                                <span class="font-w600" id="userName">Loading...</span>
                                <small class="text-end font-w400" id="userEmail">Loading...</small>
                            </div>
                        </a>
                    </li>
                    <li><a href="javascript:void()" class="active" aria-expanded="false">
                        <i class="flaticon-025-dashboard"></i>
                        <span class="nav-text">Dashboard</span>
                    </a></li>
                    <li><a href="/desk#List/Employee" aria-expanded="false">
                        <i class="flaticon-050-info"></i>
                        <span class="nav-text">Employees</span>
                    </a></li>
                    <li><a href="/desk#List/Department" aria-expanded="false">
                        <i class="flaticon-041-graph"></i>
                        <span class="nav-text">Departments</span>
                    </a></li>
                    <li><a href="/desk#List/Designation" aria-expanded="false">
                        <i class="flaticon-086-star"></i>
                        <span class="nav-text">Designations</span>
                    </a></li>
                </ul>
            </div>
        </div>

        <!-- Content Body -->
        <div class="content-body">
            <div class="container-fluid">
                <!-- Stats Cards Row -->
                <div class="row">
                    <div class="col-xl-3 col-xxl-3 col-lg-6 col-md-6 col-sm-6">
                        <div class="widget-stat card">
                            <div class="card-body p-4">
                                <div class="media ai-icon">
                                    <span class="mr-3 bgl-primary text-primary">
                                        <i class="flaticon-381-user-7"></i>
                                    </span>
                                    <div class="media-body">
                                        <h3 class="mb-0 text-black"><span class="counter ml-0" id="totalEmployees">0</span></h3>
                                        <p class="mb-0">Total Employees</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-xl-3 col-xxl-3 col-lg-6 col-md-6 col-sm-6">
                        <div class="widget-stat card">
                            <div class="card-body p-4">
                                <div class="media ai-icon">
                                    <span class="mr-3 bgl-warning text-warning">
                                        <i class="flaticon-381-calendar-1"></i>
                                    </span>
                                    <div class="media-body">
                                        <h3 class="mb-0 text-black"><span class="counter ml-0" id="activeEmployees">0</span></h3>
                                        <p class="mb-0">Active Employees</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-xl-3 col-xxl-3 col-lg-6 col-md-6 col-sm-6">
                        <div class="widget-stat card">
                            <div class="card-body p-4">
                                <div class="media ai-icon">
                                    <span class="mr-3 bgl-success text-success">
                                        <i class="flaticon-381-diamond"></i>
                                    </span>
                                    <div class="media-body">
                                        <h3 class="mb-0 text-black"><span class="counter ml-0" id="departments">0</span></h3>
                                        <p class="mb-0">Departments</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-xl-3 col-xxl-3 col-lg-6 col-md-6 col-sm-6">
                        <div class="widget-stat card">
                            <div class="card-body p-4">
                                <div class="media ai-icon">
                                    <span class="mr-3 bgl-danger text-danger">
                                        <i class="flaticon-381-heart"></i>
                                    </span>
                                    <div class="media-body">
                                        <h3 class="mb-0 text-black"><span class="counter ml-0" id="designations">0</span></h3>
                                        <p class="mb-0">Designations</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Charts Row -->
                <div class="row">
                    <div class="col-xl-6">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title">Department Distribution</h4>
                            </div>
                            <div class="card-body">
                                <canvas id="departmentChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-xl-6">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title">Gender Distribution</h4>
                            </div>
                            <div class="card-body">
                                <canvas id="genderChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-xl-6">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title">Employment Type Distribution</h4>
                            </div>
                            <div class="card-body">
                                <canvas id="employmentTypeChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-xl-6">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title">Marital Status Distribution</h4>
                            </div>
                            <div class="card-body">
                                <canvas id="maritalStatusChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Required vendors -->
    <script src="vendor/global/global.min.js"></script>
    <script src="vendor/bootstrap-select/dist/js/bootstrap-select.min.js"></script>
    <script src="vendor/chart.js/Chart.bundle.min.js"></script>
    <script src="js/custom.min.js"></script>
    <script src="js/dashboard/dashboard-1.js"></script>

    <script>
        // Initialize Frappe
        frappe.ready(function() {
            // Get user info
            frappe.call({
                method: 'frappe.auth.get_logged_user',
                callback: function(r) {
                    if (r.message) {
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'User',
                                name: r.message
                            },
                            callback: function(user) {
                                if (user.message) {
                                    document.getElementById('userName').textContent = user.message.full_name;
                                    document.getElementById('userEmail').textContent = user.message.email;
                                }
                            }
                        });
                    }
                }
            });

            // Load dashboard data
            loadDashboardData();
        });

        // Function to load all dashboard data
        function loadDashboardData() {
            // Load active employees count
            frappe.call({
                method: 'hrms.api.get_active_employees_count',
                callback: function(r) {
                    if (r.message !== undefined) {
                        document.getElementById('activeEmployees').textContent = r.message;
                    }
                }
            });

            // Load gender distribution
            frappe.call({
                method: 'hrms.api.get_gender_distribution',
                callback: function(r) {
                    if (r.message) {
                        createGenderChart(r.message);
                    }
                }
            });

            // Load comprehensive stats
            frappe.call({
                method: 'hrms.api.employee_chart.get_employee_comprehensive_stats',
                callback: function(r) {
                    if (r.message) {
                        const data = r.message;
                        
                        // Update counters
                        document.getElementById('totalEmployees').textContent = data.total_employees || 0;
                        document.getElementById('departments').textContent = data.total_departments || 0;
                        document.getElementById('designations').textContent = data.total_designations || 0;

                        // Create charts
                        if (data.department) {
                            createDepartmentChart(data.department);
                        }
                        if (data.employment_type) {
                            createEmploymentTypeChart(data.employment_type);
                        }
                        if (data.marital_status) {
                            createMaritalStatusChart(data.marital_status);
                        }
                    }
                }
            });
        }

        // Chart creation functions
        function createDepartmentChart(data) {
            const ctx = document.getElementById('departmentChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.datasets[0].values,
                        backgroundColor: [
                            '#000000',
                            '#CF0F47',
                            '#FF0B55',
                            '#FFDEDE',
                            '#00000080',
                            '#CF0F4780'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function createGenderChart(data) {
            const ctx = document.getElementById('genderChart').getContext('2d');
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Male', 'Female'],
                    datasets: [{
                        data: [data.male, data.female],
                        backgroundColor: ['#000000', '#CF0F47']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function createEmploymentTypeChart(data) {
            const ctx = document.getElementById('employmentTypeChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.datasets[0].values,
                        backgroundColor: '#FF0B55'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function createMaritalStatusChart(data) {
            const ctx = document.getElementById('maritalStatusChart').getContext('2d');
            new Chart(ctx, {
                type: 'polarArea',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.datasets[0].values,
                        backgroundColor: [
                            '#000000',
                            '#CF0F47',
                            '#FF0B55',
                            '#FFDEDE'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    </script>
</body>
</html>'''

# Create the directory if it doesn't exist
os.makedirs('apps/hrms/public/employee_dashboard', exist_ok=True)

# Write the dashboard content to the file
with open('apps/hrms/public/employee_dashboard/index.html', 'w') as f:
    f.write(dashboard_content)

print("Dashboard file created successfully!") 