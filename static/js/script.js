const allSideMenu = document.querySelectorAll('#sidebar .side-menu.top li a');

allSideMenu.forEach(item=> {
	const li = item.parentElement;

	item.addEventListener('click', function () {
		allSideMenu.forEach(i=> {
			i.parentElement.classList.remove('active');
		})
		li.classList.add('active');
	})
});


// TOGGLE SIDEBAR
const menuBar = document.querySelector('#content nav .bx.bx-menu');
const sidebar = document.getElementById('sidebar');

if (menuBar && sidebar) {
    menuBar.addEventListener('click', function () {
        console.log('Menu bar clicked');
        sidebar.classList.toggle('hide');
        console.log(sidebar.classList);
    });
}


const searchButton = document.getElementById('searchButton');
const searchForm = document.getElementById('searchForm');
const searchButtonIcon = document.getElementById('searchButtonIcon');

if (searchButton) {
	searchButton.addEventListener('click', function (e) {
		if (window.innerWidth < 576) {
			e.preventDefault();
			searchForm.classList.toggle('show');
			if (searchForm.classList.contains('show')) {
				searchButtonIcon.classList.replace('bx-search', 'bx-x');
			} else {
				searchButtonIcon.classList.replace('bx-x', 'bx-search');
			}
		}
	});
}



if(window.innerWidth < 768) {
	sidebar.classList.add('hide');
} else if(window.innerWidth > 576) {
	searchButtonIcon.classList.replace('bx-x', 'bx-search');
	searchForm.classList.remove('show');
}


window.addEventListener('resize', function () {
	if(this.innerWidth > 576) {
		searchButtonIcon.classList.replace('bx-x', 'bx-search');
		searchForm.classList.remove('show');
	}
})



const switchMode = document.getElementById('switch-mode');

switchMode.addEventListener('change', function () {
	if(this.checked) {
		document.body.classList.add('dark');
	} else {
		document.body.classList.remove('dark');
	}
})

const colorPrimary = getComputedStyle(document.documentElement)
    .getPropertyValue("--color-primary")
    .trim();

const colorLabel = getComputedStyle(document.documentElement)
    .getPropertyValue("--color-label")
    .trim();

const fontFamily = getComputedStyle(document.documentElement)
    .getPropertyValue("--font-family")
    .trim();

const defaultOptions = {

    chart: {
        toolbar: {
            show: false
        },
        zoom: {
            enabled: false
        },
        width: '100%',
        height: 180,
        offsetY: 18
    },

    dataLabels: {
        enabled: false
    }

}

let barOptions = {

    ...defaultOptions,

    chart: {
        ...defaultOptions.chart,
        type: "area"
    },

    tooltip: {
        enabled: true,
        style: {
            fontFamily: fontFamily
        },
        y: {
            formatter: value => `${value}K`
        }
    },

    series: [
        {
            name: "Views",
            data: [15, 50, 18, 90, 30, 65]
        }
    ],

    colors: [colorPrimary],

    fill: {
        type: "gradient",
        gradient: {
            type: "vertical",
            opacityFrom: 1,
            opacityTo: 0,
            stops: [0, 100],
            colorStops: [
                {
                    offset: 0,
                    opacity: .2,
                    color: "#ffffff"
                },
                {
                    offset: 100,
                    opacity: 0,
                    color: "#ffffff"
                }
            ]
        }
    },

    stroke: { colors: [colorPrimary], lineCap: "round" },

    grid: {
        borderColor: "rgba(0, 0, 0, 0)",
        padding: {
            top: -30,
            right: 0,
            bottom: -8,
            left: 12
        }
    },

    markers: {
        strokeColors: colorPrimary
    },

    yaxis: {
        show: false
    },

    xaxis: {

        labels: {
            show: true,
            floating: true,
            style: {
                colors: colorLabel,
                fontFamily: fontFamily
            }
        },

        axisBorder: {
            show: false
        },

        crosshairs: {
            show: false
        },

        categories: ["Jan", "Mar", "May", "Jul", "Sep", "Nov"]

    }

};

let chart = new ApexCharts(
    document.querySelector(".area-chart"), barOptions
);

chart.render();