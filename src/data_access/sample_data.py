"""
Sample data helpers
Populate the database with Indiana University Bloomington themed content for demos.
"""
from src.data_access.user_dal import UserDAL
from src.data_access.resource_dal import ResourceDAL
from src.data_access.message_dal import MessageDAL
from src.data_access.review_dal import ReviewDAL


SAMPLE_USERS = [
    {
        'name': 'Amelia Admin',
        'email': 'admin@iu.edu',
        'password': 'AdminPass1!',
        'role': 'admin',
        'department': 'Office of the Provost'
    },
    {
        'name': 'Shawn Staff',
        'email': 'staff@iu.edu',
        'password': 'StaffPass1!',
        'role': 'staff',
        'department': 'Campus Operations'
    },
    {
        'name': 'Sydney Student',
        'email': 'student@iu.edu',
        'password': 'StudentPass1!',
        'role': 'student',
        'department': 'Kelley School of Business'
    }
]

SAMPLE_RESOURCES = [
    {
        'title': 'Wells Library West Tower Study Suite',
        'description': (
            'Glass-enclosed study suite on the 6th floor of the Herman B Wells Library with dual monitors, '
            'ceiling mounted microphones, and soft seating for collaborative group work.'
        ),
        'category': 'Study Room',
        'location': 'Herman B Wells Library, West Tower Level 6, Bloomington, IN 47405',
        'capacity': 10,
        'equipment': 'Dual 32" displays, HDMI/USB-C, movable whiteboards, Zoom Room kit',
        'availability_rules': 'Sunday–Thursday 7:00 AM – 11:00 PM | Friday–Saturday 7:00 AM – 8:00 PM',
        'is_restricted': False,
        'owner_email': 'staff@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1529333166437-7750a6dd5a70?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1523475472560-d2df97ec485c?auto=format&fit=crop&w=1600&q=80'
        ])
    },
    {
        'title': 'Luddy School Prototyping Lab',
        'description': (
            'Hands-on prototyping lab featuring Prusa MK3 3D printers, laser cutters, soldering benches, and '
            'trained student mentors. Safety orientation required for first-time users.'
        ),
        'category': 'Lab Equipment',
        'location': 'Luddy Hall, 700 N Woodlawn Ave, Bloomington, IN 47408',
        'capacity': 24,
        'equipment': '3D printers, Glowforge laser cutter, PCB rework station, Oculus headsets',
        'availability_rules': 'Weekdays 9:00 AM – 9:00 PM with staff present; reservations limited to 3 hours',
        'is_restricted': True,
        'owner_email': 'staff@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1600&q=80'
        ])
    },
    {
        'title': 'IU Auditorium Main Stage',
        'description': (
            'Iconic performance venue suited for large lectures, concerts, and ceremonies. Includes stage lighting, '
            'full sound reinforcement, and backstage green rooms.'
        ),
        'category': 'Event Space',
        'location': '1211 E 7th St, Bloomington, IN 47405',
        'capacity': 3200,
        'equipment': 'Concert-grade audio, theatrical lighting, dual projection, Steinway grand piano',
        'availability_rules': 'Submit requests at least 14 days in advance; staff approval required',
        'is_restricted': True,
        'owner_email': 'admin@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=1600&q=80'
        ])
    },
    {
        'title': 'Kelley School Podcast Studio',
        'description': (
            'Sound-treated recording studio with RODECaster Pro II mixer, dynamic microphones, and video capture '
            'lighting for polished podcasts or interview content.'
        ),
        'category': 'AV Equipment',
        'location': 'Hodge Hall 2030, Kelley School of Business, Bloomington, IN 47405',
        'capacity': 6,
        'equipment': 'RODECaster Pro II, Shure SM7B mics, 4K PTZ camera, acoustic treatment, lighting grid',
        'availability_rules': 'Bookings auto-approved for staff; students require a Kelley faculty sponsor',
        'is_restricted': True,
        'owner_email': 'admin@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1518552781905-998e991dedc0?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1600&q=80'
        ])
    },
    {
        'title': 'SRSC Court 6 (Recreation Pickup)',
        'description': (
            'Multi-purpose hardwood court inside the Student Recreational Sports Center ideal for club practices or '
            'intramural tournaments. Portable bleachers available upon request.'
        ),
        'category': 'Event Space',
        'location': 'SRSC, 1025 E 7th St, Bloomington, IN 47405',
        'capacity': 150,
        'equipment': 'Scoreboard, portable PA, divider netting, rolling bleachers',
        'availability_rules': 'Bookings available in 90-minute blocks; facility team confirms within 2 business days',
        'is_restricted': False,
        'owner_email': 'staff@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1505843513577-22bb7d21e455?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1519861531473-9200262188bf?auto=format&fit=crop&w=1600&q=80'
        ])
    },
    {
        'title': 'IMU Georgian Room Collaboration Hall',
        'description': (
            'Recently renovated Georgian Room inside the Indiana Memorial Union featuring flexible seating, '
            'ceiling mounted projectors, and adjacent catering support for design sprints or leadership offsites.'
        ),
        'category': 'Event Space',
        'location': '900 E 7th St, Bloomington, IN 47405',
        'capacity': 120,
        'equipment': 'Dual laser projectors, zoned audio, modular tables, on-call catering',
        'availability_rules': 'Reservations approved by the IMU events desk; submit at least 7 days ahead',
        'is_restricted': True,
        'owner_email': 'staff@iu.edu',
        'images': ','.join([
            'https://images.unsplash.com/photo-1448932223592-d1fc686e76ea?auto=format&fit=crop&w=1600&q=80',
            'https://images.unsplash.com/photo-1470229538611-16ba8c7ffbd7?auto=format&fit=crop&w=1600&q=80'
        ])
    }
]

SAMPLE_MESSAGES = [
    {
        'resource_title': 'Wells Library West Tower Study Suite',
        'messages': [
            {
                'sender': 'student@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'Hi! Could my capstone team reserve the Wells suite on Thursday evening for a design sprint?'
            },
            {
                'sender': 'staff@iu.edu',
                'receiver': 'student@iu.edu',
                'content': 'Absolutely. I blocked 6–8 PM for you and added the rolling whiteboard you requested.'
            },
            {
                'sender': 'student@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'Perfect, thank you for the quick turnaround!'
            }
        ]
    },
    {
        'resource_title': 'IU Auditorium Main Stage',
        'messages': [
            {
                'sender': 'staff@iu.edu',
                'receiver': 'admin@iu.edu',
                'content': 'Our leadership forum wants the main stage on March 8. Is that date free?'
            },
            {
                'sender': 'admin@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'March 8 works. I will connect you with production support for lights and livestream setup.'
            }
        ]
    },
    {
        'resource_title': 'SRSC Court 6 (Recreation Pickup)',
        'messages': [
            {
                'sender': 'student@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'Could Hoosier eSports reserve Court 6 next Friday for a charity dodgeball event?'
            },
            {
                'sender': 'staff@iu.edu',
                'receiver': 'student@iu.edu',
                'content': 'That sounds fun! Court 6 is free after 8 PM. Please submit the booking with the expected headcount.'
            }
        ]
    },
    {
        'resource_title': 'Kelley School Podcast Studio',
        'messages': [
            {
                'sender': 'admin@iu.edu',
                'receiver': 'student@iu.edu',
                'content': 'You are approved for the podcast studio at 2 PM. Do you need an operator on site?'
            },
            {
                'sender': 'student@iu.edu',
                'receiver': 'admin@iu.edu',
                'content': 'Thank you! A quick orientation when we arrive would be perfect.'
            }
        ]
    },
    {
        'resource_title': 'Luddy School Prototyping Lab',
        'messages': [
            {
                'sender': 'staff@iu.edu',
                'receiver': 'admin@iu.edu',
                'content': 'We have a wave of capstone builds coming. May we extend lab hours next Wednesday?'
            },
            {
                'sender': 'admin@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'Approved. I noted the change on the resource page so students see the extra availability.'
            }
        ]
    },
    {
        'resource_title': 'IMU Georgian Room Collaboration Hall',
        'messages': [
            {
                'sender': 'student@iu.edu',
                'receiver': 'staff@iu.edu',
                'content': 'Could we host the student leadership retreat in the Georgian Room next month?'
            },
            {
                'sender': 'staff@iu.edu',
                'receiver': 'student@iu.edu',
                'content': 'Yes, submit the booking so we can loop in IMU catering. I will earmark the date until paperwork arrives.'
            }
        ]
    }
]

SAMPLE_REVIEWS = [
    {
        'resource_title': 'Wells Library West Tower Study Suite',
        'reviews': [
            {
                'reviewer': 'student@iu.edu',
                'rating': 5,
                'comment': 'Amazing view of campus and plenty of screens for hybrid collaboration.'
            },
            {
                'reviewer': 'staff@iu.edu',
                'rating': 4,
                'comment': 'Technology is solid, just book a little early because it fills fast.'
            }
        ]
    },
    {
        'resource_title': 'Luddy School Prototyping Lab',
        'reviews': [
            {
                'reviewer': 'student@iu.edu',
                'rating': 5,
                'comment': 'Mentors walked us through laser cutter safety and we finished our mock-up in one sitting.'
            }
        ]
    },
    {
        'resource_title': 'IU Auditorium Main Stage',
        'reviews': [
            {
                'reviewer': 'staff@iu.edu',
                'rating': 5,
                'comment': 'Production support was flawless for our leadership summit.'
            },
            {
                'reviewer': 'admin@iu.edu',
                'rating': 4,
                'comment': 'Acoustics are great, but schedule well ahead to coordinate crews.'
            }
        ]
    },
    {
        'resource_title': 'Kelley School Podcast Studio',
        'reviews': [
            {
                'reviewer': 'student@iu.edu',
                'rating': 5,
                'comment': 'Studio lighting and audio chain made our podcast sound professional.'
            }
        ]
    },
    {
        'resource_title': 'SRSC Court 6 (Recreation Pickup)',
        'reviews': [
            {
                'reviewer': 'student@iu.edu',
                'rating': 4,
                'comment': 'Plenty of bleachers and the staff helped with setup.'
            }
        ]
    },
    {
        'resource_title': 'IMU Georgian Room Collaboration Hall',
        'reviews': [
            {
                'reviewer': 'staff@iu.edu',
                'rating': 5,
                'comment': 'Flexible layout let us run breakout stations without any extra furniture rentals.'
            }
        ]
    }
]


def ensure_sample_content():
    """Create demo users/resources if they do not exist."""
    user_lookup = {}
    for user in SAMPLE_USERS:
        record = UserDAL.get_user_by_email(user['email'])
        if record is None:
            record = UserDAL.create_user(
                name=user['name'],
                email=user['email'],
                password=user['password'],
                role=user['role'],
                department=user['department']
            )
        else:
            # Ensure stored role/department stay aligned with the sample expectations
            needs_update = False
            updates = {}
            if record.role != user['role']:
                updates['role'] = user['role']
                needs_update = True
            if user['department'] and record.department != user['department']:
                updates['department'] = user['department']
                needs_update = True
            if needs_update:
                UserDAL.update_user(record.user_id, **updates)
                record = UserDAL.get_user_by_id(record.user_id)
        user_lookup[user['email']] = record

    created_count = 0
    resource_lookup = {}
    for resource in SAMPLE_RESOURCES:
        existing = ResourceDAL.get_resource_by_title(resource['title'])
        if existing:
            resource_lookup[resource['title']] = existing
            continue
        owner = user_lookup.get(resource['owner_email'])
        if not owner:
            continue
        created = ResourceDAL.create_resource(
            owner_id=owner.user_id,
            title=resource['title'],
            description=resource['description'],
            category=resource['category'],
            location=resource['location'],
            capacity=resource['capacity'],
            images=resource.get('images'),
            equipment=resource['equipment'],
            availability_rules=resource['availability_rules'],
            is_restricted=resource['is_restricted'],
            status='published'
        )
        resource_lookup[resource['title']] = created
        created_count += 1

    if not resource_lookup:
        for resource in SAMPLE_RESOURCES:
            existing = ResourceDAL.get_resource_by_title(resource['title'])
            if existing:
                resource_lookup[resource['title']] = existing

    seed_sample_messages(user_lookup, resource_lookup)
    seed_sample_reviews(user_lookup, resource_lookup)

    if created_count:
        print(f'✓ Added {created_count} IU Bloomington sample resources')
    else:
        print('✓ Sample resources already present')


def seed_sample_messages(user_lookup, resource_lookup):
    """Populate demo message threads if they have not been seeded yet."""
    for convo in SAMPLE_MESSAGES:
        resource = resource_lookup.get(convo['resource_title'])
        if not resource or not convo['messages']:
            continue

        first_msg = convo['messages'][0]
        sender = user_lookup.get(first_msg['sender'])
        receiver = user_lookup.get(first_msg['receiver'])
        if not sender or not receiver:
            continue

        thread_id = MessageDAL.ensure_thread(sender.user_id, receiver.user_id, resource.resource_id)
        existing_messages = MessageDAL.get_thread_messages(thread_id)
        if existing_messages:
            continue

        for message in convo['messages']:
            sender_user = user_lookup.get(message['sender'])
            receiver_user = user_lookup.get(message['receiver'])
            if not sender_user or not receiver_user:
                continue
            MessageDAL.create_message(
                sender_id=sender_user.user_id,
                receiver_id=receiver_user.user_id,
                content=message['content'],
                thread_id=thread_id,
                resource_id=resource.resource_id
            )


def seed_sample_reviews(user_lookup, resource_lookup):
    """Populate a baseline set of reviews for demo resources."""
    for entry in SAMPLE_REVIEWS:
        resource = resource_lookup.get(entry['resource_title'])
        if not resource:
            continue
        existing_reviews = ReviewDAL.get_reviews_by_resource(resource.resource_id)
        if existing_reviews:
            continue

        for review in entry.get('reviews', []):
            reviewer = user_lookup.get(review['reviewer'])
            if not reviewer:
                continue
            ReviewDAL.create_review(
                resource_id=resource.resource_id,
                reviewer_id=reviewer.user_id,
                rating=review['rating'],
                comment=review.get('comment')
            )
