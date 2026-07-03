:: =============================================================================
:: setup_db.bat — One-click PostgreSQL database setup for Windows
:: Double-click this file OR run it in terminal
:: =============================================================================
@echo off
echo ============================================
echo  Setting up PostgreSQL for Broker Service
echo ============================================

:: Try password "abhi" first
echo Trying password: abhi
psql -U postgres -c "CREATE DATABASE stock_portfolio;" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Trying password: Abhi
    set PGPASSWORD=Abhi
    psql -U postgres -c "CREATE DATABASE stock_portfolio;" 2>NUL
) else (
    set PGPASSWORD=abhi
)

echo.
echo Running setup SQL...
psql -U postgres -d stock_portfolio -f setup_db.sql

echo.
echo Done! Check output above for errors.
pause
