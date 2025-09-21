# OrderFlow

Order management system with Telegram integration for tracking and managing product orders with real-time notifications.

## 🚀 Technologies

### Backend
- **Django 5.1.6** - Web framework
- **PostgreSQL** - Primary database (with psycopg2-binary)
- **SQLite** - Development database
- **Python 3.x** - Programming language

### Frontend
- **HTML5** - Markup
- **CSS3** - Styling
- **JavaScript** - Client-side functionality
- **Bootstrap** - UI framework

### Integrations
- **Telegram Bot API** - Real-time notifications
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

### Additional Libraries
- **python-dotenv** - Environment variable management
- **requests** - HTTP library for API calls
- **asgiref** - ASGI support

## 📋 Features

### Order Management
- **Create Orders** - Add new product orders with detailed specifications
- **Order Tracking** - Track order status through multiple stages:
  - New (Нове)
  - Embroidery (На вишивці)
  - Almost Finished (Майже готове)
  - Finished (Готове)
  - On Hold (Призупинено)
- **Order History** - Complete audit trail of status changes
- **Bulk Status Updates** - Update multiple orders simultaneously

### Product Management
- **Product Models** - Manage different product types
- **Color Management** - Track available colors with:
  - Color codes
  - Availability status (In Stock, Low Stock, Out of Stock)
  - Real-time inventory tracking

### User Management
- **Custom User Model** - Extended user model with Telegram integration
- **Authentication** - Secure login/logout system
- **Profile Management** - User profile customization
- **Password Management** - Secure password change functionality

### Notification System
- **Telegram Integration** - Real-time notifications via Telegram bot
- **Smart Notifications** - Configurable notification settings:
  - Order creation notifications
  - Order completion notifications
  - Working hours pause (8:00 - 18:00)
  - Delayed notification system for after-hours orders
- **User Preferences** - Individual notification settings per user

### Order Features
- **Order Details** - Comprehensive order information:
  - Product model and color
  - Embroidery option
  - Comments and notes
  - Urgent flag
  - Etsy integration flag
  - Creation and completion timestamps
- **Order Filtering** - Separate views for current and finished orders
- **Pagination** - Efficient handling of large order lists

## 🏗️ Project Structure

```
OrderFlow/
├── OrderFlow/           # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py         # URL routing
│   └── wsgi.py         # WSGI configuration
├── orders/             # Main application
│   ├── models.py       # Database models
│   ├── views.py        # View logic
│   ├── forms.py        # Form definitions
│   ├── urls.py         # App URL routing
│   ├── telegram_bot.py # Telegram bot integration
│   └── utils.py        # Utility functions
├── templates/          # HTML templates
├── static/            # Static files (CSS, JS, images)
├── requirements.txt   # Python dependencies
├── Dockerfile        # Docker configuration
├── docker-compose.yml # Multi-container setup
└── manage.py         # Django management script
```

---

**OrderFlow** - Streamlining order management with modern web technologies and real-time notifications.
