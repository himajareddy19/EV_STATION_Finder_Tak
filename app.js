
require([
    "esri/Map",
    "esri/views/MapView",
    "esri/layers/GeoJSONLayer"
], function (Map, MapView, GeoJSONLayer) {

    // 1. Create the map
    const map = new Map({
        basemap: "streets-vector"
    });

    // 2. Display the map on Chennai
    const view = new MapView({
        container: "viewDiv",
        map: map,
        center: [80.2707, 13.0827],
        zoom: 11
    });

    // 3. Create the EV stations layer
    const stationsLayer = new GeoJSONLayer({
        url: "/Data/stations.geojson",
        title: "EV Charging Stations",

        // 4. Station popup details
        popupTemplate: {
            title: "{name}",

            expressionInfos: [
                {
                    name: "zoneDisplay",
                    title: "Zone",
                    expression: `
                        IIF(
                            IsEmpty($feature.zone_id),
                            'Not Available',
                            $feature.zone_id
                        )
                    `
                }
            ],

            content: `
                <b>Station ID:</b> {station_id}<br>
                <b>Operator:</b> {operator}<br>
                <b>Connector:</b> {connector_type}<br>
                <b>Power:</b> {power_kw} kW<br>
                <b>Zone:</b> {expression/zoneDisplay}
            `
        },

        // 5. Color stations based on power
        renderer: {
            type: "class-breaks",
            field: "power_kw",

            classBreakInfos: [
                {
                    minValue: 0,
                    maxValue: 14.99,
                    symbol: {
                        type: "simple-marker",
                        size: 9,
                        color: "#3186D8",
                        outline: {
                            color: "white",
                            width: 1
                        }
                    },
                    label: "Low Power (<15 kW)"
                },
                {
                    minValue: 15,
                    maxValue: 50,
                    symbol: {
                        type: "simple-marker",
                        size: 9,
                        color: "#E5A12B",
                        outline: {
                            color: "white",
                            width: 1
                        }
                    },
                    label: "Medium Power (15–50 kW)"
                },
                {
                    minValue: 50.01,
                    maxValue: 10000,
                    symbol: {
                        type: "simple-marker",
                        size: 9,
                        color: "#299764",
                        outline: {
                            color: "white",
                            width: 1
                        }
                    },
                    label: "High Power (>50 kW)"
                }
            ]
        },

        // 6. Enable clustering initially
       featureReduction: {
    type: "cluster",
    clusterRadius: "100px",

    fields: [
        {
            name: "SUM_power_kw",
            alias: "Total Power (kW)",
            onStatisticField: "power_kw",
            statisticType: "sum"
        }
    ],

    popupTemplate: {
        title: "EV Station Cluster",
        content: `
            <b>Number of Stations:</b> {cluster_count}<br>
            <b>Total Power:</b> {SUM_power_kw} kW
        `
    }
}
    });

    // 7. Add stations to the map
    map.add(stationsLayer);

    // 8. Zoom to stations and populate connector dropdown
    stationsLayer.load()
        .then(function () {

            console.log("Stations loaded successfully");

            return stationsLayer.queryFeatures({
                where: "1=1",
                outFields: ["connector_type"],
                returnGeometry: false
            });

        })
        .then(function (result) {

            const connectorDropdown =
                document.getElementById("connectorFilter");

            const connectorTypes = [
                ...new Set(
                    result.features
                        .map(function (feature) {
                            return feature.attributes.connector_type;
                        })
                        .filter(Boolean)
                )
            ];

            connectorTypes.sort();

            connectorTypes.forEach(function (connector) {
                const option = document.createElement("option");

                option.value = connector;
                option.textContent = connector;

                connectorDropdown.appendChild(option);
            });

            return stationsLayer.queryExtent();
        })
        .then(function (result) {
            if (result.extent) {
                view.goTo(result.extent.expand(1.3));
            }
        })
        .catch(function (error) {
            console.error("Stations loading error:", error);
        });

    // 9. Connector and minimum power filters
    const connectorDropdown =
        document.getElementById("connectorFilter");

    const minPowerDropdown =
        document.getElementById("minPowerFilter");

    function applyStationFilters() {

        const selectedConnector = connectorDropdown.value;
        const minPower = Number(minPowerDropdown.value);

        let whereClause = "1=1";

        if (selectedConnector !== "all") {

            const safeConnector =
                selectedConnector.replace(/'/g, "''");

            whereClause +=
                " AND connector_type = '" +
                safeConnector +
                "'";
        }

        whereClause += " AND power_kw >= " + minPower;

        stationsLayer.definitionExpression = whereClause;
    }

    connectorDropdown.addEventListener(
        "change",
        applyStationFilters
    );

    minPowerDropdown.addEventListener(
        "change",
        applyStationFilters
    );

    // 10. Clustering ON/OFF checkbox
    const clusterToggle =
        document.getElementById("clusterToggle");

    clusterToggle.checked = true;

    clusterToggle.addEventListener("change", function () {

        if (clusterToggle.checked) {

    stationsLayer.featureReduction = {
        type: "cluster",
        clusterRadius: "100px",

        fields: [
            {
                name: "SUM_power_kw",
                alias: "Total Power (kW)",
                onStatisticField: "power_kw",
                statisticType: "sum"
            }
        ],

        popupTemplate: {
            title: "EV Station Cluster",
            content: `
                <b>Number of Stations:</b> {cluster_count}<br>
                <b>Total Power:</b> {SUM_power_kw} kW
            `
        }
    };

} else {

    stationsLayer.featureReduction = null;

}
    });

});

